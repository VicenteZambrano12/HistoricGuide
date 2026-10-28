import assert from 'node:assert/strict';
import { beforeEach, test } from 'node:test';
import { apiRequest } from './http.js';
import { getErrorContext, logger } from './logger.js';
import { sendChatRequest } from './api.js';

beforeEach((t) => {
  for (const level of ['debug', 'info', 'warn', 'error']) t.mock.method(logger, level, () => {});
});

test('HTTP wrapper sends matching UUID headers and uses backend response IDs', async (t) => {
  let generated;
  t.mock.method(globalThis, 'fetch', async (_path, options) => {
    generated = options.headers.get('X-Correlation-ID');
    assert.match(generated, /^[0-9a-f-]{36}$/);
    assert.equal(options.headers.get('X-Request-ID'), generated);
    assert.equal(options.headers.get('Accept'), 'application/json');
    return Response.json({ ok: true }, { headers: {
      'X-Correlation-ID': 'backend-correlation',
      'X-Request-ID': 'backend-request'
    } });
  });
  const result = await apiRequest('/api/health?private=value', {
    headers: { Accept: 'application/json' }
  }, (response) => response.json());
  assert.deepEqual(result, { ok: true });
  const record = logger.info.mock.calls.at(-1).arguments[1];
  assert.equal(record.correlationId, 'backend-correlation');
  assert.equal(record.requestId, 'backend-request');
  assert.equal(record.clientCorrelationId, generated);
  assert.equal(record.route, '/api/health');
  assert.equal(record.status, 200);
  assert.ok(record.durationMs >= 0);
});

test('FastAPI X-Request-ID and missing headers fall back without losing tracing', async (t) => {
  for (const serverId of ['backend-request', null]) {
    let generated;
    const fetchMock = t.mock.method(globalThis, 'fetch', async (_path, options) => {
      generated = options.headers.get('X-Request-ID');
      return Response.json({}, { headers: serverId ? { 'X-Request-ID': serverId } : {} });
    });
    await apiRequest('/api/health', {}, (response) => response.json());
    const record = logger.info.mock.calls.at(-1).arguments[1];
    assert.equal(record.correlationId, serverId ?? generated);
    assert.equal(record.requestId, serverId ?? generated);
    fetchMock.mock.restore();
  }
});

test('malformed response IDs warn and use the generated trace instead', async (t) => {
  t.mock.method(globalThis, 'fetch', async () => Response.json({}, {
    headers: { 'X-Correlation-ID': 'bad id with spaces' }
  }));
  await apiRequest('/api/health', {}, (response) => response.json());
  assert.equal(logger.warn.mock.calls[0].arguments[0], 'http.invalid_trace_header');
  assert.match(logger.info.mock.calls.at(-1).arguments[1].correlationId, /^[0-9a-f-]{36}$/);
});

test('network failures retain error identity and generated correlation ID', async (t) => {
  const failure = new TypeError('Network unavailable');
  t.mock.method(globalThis, 'fetch', async () => { throw failure; });
  await assert.rejects(apiRequest('/api/chat', { method: 'POST' }, () => {}), (error) => error === failure);
  assert.match(getErrorContext(failure).correlationId, /^[0-9a-f-]{36}$/);
  assert.equal(logger.error.mock.calls[0].arguments[0], 'http.request_failed');
});

test('concurrent response parsing failures retain their own backend IDs', async (t) => {
  t.mock.method(globalThis, 'fetch', async (path) => Response.json({}, {
    headers: { 'X-Request-ID': path.endsWith('first') ? 'trace-first' : 'trace-second' }
  }));
  let release;
  const gate = new Promise((resolve) => { release = resolve; });
  const firstError = new Error('First parse failure');
  const secondError = new Error('Second parse failure');
  const first = apiRequest('/api/first', {}, async () => {
    await gate;
    throw firstError;
  });
  const second = apiRequest('/api/second', {}, async () => {
    release();
    throw secondError;
  });
  await Promise.allSettled([first, second]);
  assert.equal(getErrorContext(firstError).correlationId, 'trace-first');
  assert.equal(getErrorContext(secondError).correlationId, 'trace-second');
});

test('explicit cancellation is debug-only while timeouts are errors', async (t) => {
  for (const name of ['AbortError', 'TimeoutError']) {
    const controller = new AbortController();
    controller.abort(new DOMException('Request stopped', name));
    const fetchMock = t.mock.method(globalThis, 'fetch', async (_path, { signal }) => {
      signal.throwIfAborted();
    });
    const before = logger.error.mock.callCount();
    await assert.rejects(apiRequest('/api/chat', { signal: controller.signal }, () => {}), { name });
    assert.equal(logger.error.mock.callCount(), before + (name === 'TimeoutError' ? 1 : 0));
    fetchMock.mock.restore();
  }
});

test('chat HTTP, JSON, streamed error, and interrupted stream failures retain server tracing', async (t) => {
  for (const response of [
    Response.json({ detail: 'Unavailable' }, { status: 503 }),
    new Response('invalid json', { headers: { 'Content-Type': 'application/json' } }),
    new Response('{"type":"error","detail":"Stream failed"}\n', { headers: { 'Content-Type': 'application/x-ndjson' } }),
    new Response('{"type":"progress","step":"generating"}\n', { headers: { 'Content-Type': 'application/x-ndjson' } })
  ]) {
    response.headers.set('X-Request-ID', 'trace-chat-failure');
    const fetchMock = t.mock.method(globalThis, 'fetch', async () => response);
    const isStream = response.headers.get('content-type').includes('ndjson');
    await assert.rejects(sendChatRequest({
      stop: 'Pantheon', mode: 'text', query: 'Question',
      ...(isStream ? { onProgress: () => {} } : {})
    }), (error) => {
      assert.equal(getErrorContext(error).correlationId, 'trace-chat-failure');
      return true;
    });
    fetchMock.mock.restore();
  }
});

test('audio results carry response trace context for subsequent playback failures', async (t) => {
  t.mock.method(globalThis, 'fetch', async () => new Response('wav-data', {
    headers: { 'Content-Type': 'audio/wav', 'X-Request-ID': 'audio-trace' }
  }));
  const { audio } = await sendChatRequest({ stop: 'Pantheon', mode: 'tts', query: 'Question' });
  assert.equal(getErrorContext(audio).requestId, 'audio-trace');
  assert.equal(logger.info.mock.calls.at(-1).arguments[0], 'http.request_completed');
});
