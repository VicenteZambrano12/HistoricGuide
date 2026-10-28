import assert from 'node:assert/strict';
import { test } from 'node:test';
import { checkBackendHealth, sendChatRequest } from './api.js';
import { ROME_STOPS } from './romeStopsData.js';

test('checks the backend health endpoint without caching', async (t) => {
  const fetchMock = t.mock.method(globalThis, 'fetch', async (url, options) => {
    assert.equal(url, '/api/health');
    assert.equal(options.cache, 'no-store');
    assert.ok(options.signal instanceof AbortSignal);
    return Response.json({ status: 'ok' });
  });

  assert.deepEqual(await checkBackendHealth(), { status: 'ok' });
  assert.equal(fetchMock.mock.callCount(), 1);
});

test('rejects unsuccessful HTTP responses', async (t) => {
  t.mock.method(globalThis, 'fetch', async () => new Response('', { status: 503 }));
  await assert.rejects(checkBackendHealth(), /HTTP 503/);
});

test('rejects an unexpected health status or missing status', async (t) => {
  for (const body of [{ status: 'down' }, {}, null]) {
    const fetchMock = t.mock.method(globalThis, 'fetch', async () => Response.json(body));
    await assert.rejects(checkBackendHealth(), /unexpected response/);
    fetchMock.mock.restore();
  }
});

test('rejects invalid JSON responses', async (t) => {
  t.mock.method(globalThis, 'fetch', async () => new Response('<html>Not the API</html>'));
  await assert.rejects(checkBackendHealth(), SyntaxError);
});

test('propagates network errors', async (t) => {
  t.mock.method(globalThis, 'fetch', async () => {
    throw new TypeError('Failed to fetch');
  });
  await assert.rejects(checkBackendHealth(), /Failed to fetch/);
});

test('passes cancellation through to the request', async (t) => {
  const controller = new AbortController();
  controller.abort();
  t.mock.method(globalThis, 'fetch', async (_url, { signal }) => {
    signal.throwIfAborted();
  });
  await assert.rejects(checkBackendHealth(controller.signal), { name: 'AbortError' });
});

test('limits the request to five seconds', async (t) => {
  const controller = new AbortController();
  controller.abort(new DOMException('Health check timed out', 'TimeoutError'));
  t.mock.method(AbortSignal, 'timeout', (milliseconds) => {
    assert.equal(milliseconds, 5000);
    return controller.signal;
  });
  t.mock.method(globalThis, 'fetch', async (_url, { signal }) => {
    signal.throwIfAborted();
  });
  await assert.rejects(checkBackendHealth(), { name: 'TimeoutError' });
});

const chat = {
  stop: 'Pantheon',
  requestType: 'historic',
  mode: 'text',
  query: 'Tell me about this monument.'
};

function progressResponse(events) {
  return new Response(events.map((event) => JSON.stringify(event)).join('\n') + '\n', {
    headers: { 'content-type': 'application/x-ndjson' }
  });
}

test('preserves PDF page references for JSON, streamed text, and all audio outputs', async (t) => {
  const sources = [{ source: 'Pantheon/historic/guide.pdf', page: 7 }];
  for (const stream of [false, true]) {
    for (const mode of ['text', 'stt', 'tts', 'full']) {
      const audioOutput = mode === 'tts' || mode === 'full';
      const fetchMock = t.mock.method(globalThis, 'fetch', async () => {
        if (stream) {
          return progressResponse([audioOutput
            ? { type: 'result', audio: btoa('wav-data'), mime_type: 'audio/wav', sources }
            : { type: 'result', text: 'Answer', sources }]);
        }
        return audioOutput
          ? new Response('wav-data', {
            headers: { 'content-type': 'audio/wav', 'X-PDF-Sources': JSON.stringify(sources) }
          })
          : Response.json({ text: 'Answer', sources });
      });
      const result = await sendChatRequest({
        ...chat, mode,
        query: mode === 'stt' || mode === 'full'
          ? new Blob(['voice'], { type: 'audio/webm' }) : chat.query,
        ...(stream ? { onProgress() {} } : {})
      });
      assert.deepEqual(result.sources, sources);
      fetchMock.mock.restore();
    }
  }
});

test('invalid PDF references are shown as an error, not a successful answer', async (t) => {
  t.mock.method(globalThis, 'fetch', async () => progressResponse([
    { type: 'result', text: 'Answer', sources: [{ source: '../private.pdf', page: 1 }] }
  ]));
  await assert.rejects(sendChatRequest({ ...chat, onProgress() {} }), /invalid PDF references/);
});

test('streams progress before the answer and handles split UTF-8 and JSON chunks', async (t) => {
  let stream;
  const steps = [];
  t.mock.method(globalThis, 'fetch', async (_url, { body }) => {
    assert.equal(body.get('stream'), 'true');
    return new Response(new ReadableStream({ start(controller) { stream = controller; } }), {
      headers: { 'content-type': 'application/x-ndjson' }
    });
  });
  let receivedProgress;
  const progress = new Promise((resolve) => { receivedProgress = resolve; });
  const request = sendChatRequest({
    ...chat,
    onProgress(step) { steps.push(step); receivedProgress(); }
  });
  await Promise.resolve();
  const encoder = new TextEncoder();
  stream.enqueue(encoder.encode('{"type":"progress","step":"retriev'));
  stream.enqueue(encoder.encode('ing"}\n'));
  await progress;
  assert.deepEqual(steps, ['retrieving']);
  const result = encoder.encode('{"type":"result","text":"Guía de Roma"}');
  const accented = result.indexOf(0xc3);
  stream.enqueue(result.slice(0, accented + 1));
  stream.enqueue(result.slice(accented + 1));
  stream.close();
  assert.deepEqual(await request, { text: 'Guía de Roma' });
});

test('decodes streamed audio answers in both audio-output modes', async (t) => {
  t.mock.method(globalThis, 'fetch', async () => progressResponse([
    { type: 'progress', step: 'synthesizing' },
    { type: 'result', audio: btoa('wav-data'), mime_type: 'audio/wav' }
  ]));
  for (const mode of ['tts', 'full']) {
    const steps = [];
    const result = await sendChatRequest({
      ...chat, mode, onProgress: (step) => steps.push(step),
      query: mode === 'full' ? new Blob(['voice'], { type: 'audio/webm' }) : chat.query
    });
    assert.deepEqual(steps, ['synthesizing']);
    assert.equal(result.audio.type, 'audio/wav');
    assert.equal(await result.audio.text(), 'wav-data');
  }
});

test('stream errors, invalid events, and incomplete streams never become answers', async (t) => {
  for (const [events, expected] of [
    [[{ type: 'error', detail: 'Processing failed' }], /Processing failed/],
    [[{ type: 'progress', step: 'generating' }], /before an answer/],
    [[{ type: 'progress', step: 'invented' }], /invalid progress/],
    [[{ type: 'result', text: ' ' }], /unexpected text/],
    [[{ type: 'result', audio: btoa('wav'), mime_type: 'audio/wav' }], /unexpected text/],
    [[null], /invalid progress/]
  ]) {
    const fetchMock = t.mock.method(globalThis, 'fetch', async () => progressResponse(events));
    await assert.rejects(sendChatRequest({ ...chat, onProgress() {} }), expected);
    fetchMock.mock.restore();
  }
});

test('cancelling a stream rejects without delivering late progress or a result', async (t) => {
  const controller = new AbortController();
  let delivered;
  const progress = new Promise((resolve) => { delivered = resolve; });
  const steps = [];
  t.mock.method(globalThis, 'fetch', async (_url, { signal }) => new Response(
    new ReadableStream({
      start(stream) {
        signal.addEventListener('abort', () => stream.error(signal.reason), { once: true });
        stream.enqueue(new TextEncoder().encode('{"type":"progress","step":"routing"}\n'));
      }
    }), { headers: { 'content-type': 'application/x-ndjson' } }
  ));
  const request = sendChatRequest({
    ...chat, onProgress(step) { steps.push(step); delivered(); }
  }, controller.signal);
  await progress;
  controller.abort();
  await assert.rejects(request, { name: 'AbortError' });
  assert.deepEqual(steps, ['routing']);
});

test('freeform text and voice requests let the backend select the topic', async (t) => {
  const fetchMock = t.mock.method(globalThis, 'fetch', async (_url, { body }) => {
    assert.equal(body.has('request_type'), false);
    assert.equal(body.get('language'), 'EN');
    return body.get('mode') === 'full'
      ? new Response('wav-data', { headers: { 'content-type': 'audio/wav' } })
      : Response.json({ text: 'Answer' });
  });
  await sendChatRequest({ ...chat, requestType: undefined });
  await sendChatRequest({
    ...chat, requestType: undefined, mode: 'full',
    query: new File(['voice'], 'voice-message.webm', { type: 'audio/webm' })
  });
  assert.equal(fetchMock.mock.callCount(), 2);
});

test('sends all chat fields as multipart in every mode for both topics', async (t) => {
  for (const mode of ['text', 'tts', 'stt', 'full']) {
    for (const requestType of ['historic', 'restaurant']) {
      const audioInput = mode === 'stt' || mode === 'full';
      const audioOutput = mode === 'tts' || mode === 'full';
      const query = audioInput
        ? new File(['recording'], 'question.wav', { type: 'audio/wav' })
        : chat.query;
      const fetchMock = t.mock.method(globalThis, 'fetch', async (url, options) => {
        assert.equal(url, '/api/chat');
        assert.equal(options.method, 'POST');
        assert.equal(options.headers, undefined);
        assert.ok(options.signal instanceof AbortSignal);
        const fields = options.body;
        assert.ok(fields instanceof FormData);
        assert.deepEqual([...fields.keys()].sort(),
          ['language', 'mode', 'query', 'request_type', 'stop']);
        assert.equal(fields.get('stop'), 'Pantheon');
        assert.equal(fields.get('request_type'), requestType);
        assert.equal(fields.get('language'), 'EN');
        assert.equal(fields.get('mode'), mode);
        if (audioInput) {
          assert.equal(fields.get('query').name, 'question.wav');
          assert.equal(fields.get('query').type, 'audio/wav');
          assert.equal(await fields.get('query').text(), 'recording');
        } else {
          assert.equal(fields.get('query'), chat.query);
        }
        return audioOutput
          ? new Response('wav-data', { headers: { 'content-type': 'audio/wav' } })
          : Response.json({ text: 'Guide answer' });
      });
      const result = await sendChatRequest({ ...chat, mode, requestType, query });
      if (audioOutput) {
        assert.equal(result.audio.type, 'audio/wav');
        assert.equal(await result.audio.text(), 'wav-data');
      } else {
        assert.deepEqual(result, { text: 'Guide answer' });
      }
      fetchMock.mock.restore();
    }
  }
});

test('all tour stops use the exact backend corpus keys', () => {
  assert.deepEqual(ROME_STOPS.map((stop) => stop.apiStop), [
    'Torre_Argentina', 'Forum_Boarium', 'Roman_Forum', 'Trajans_Markets', 'Pantheon'
  ]);
});

test('sends Spanish for every chat mode, with and without an explicit topic', async (t) => {
  for (const mode of ['text', 'tts', 'stt', 'full']) {
    for (const requestType of [undefined, 'historic', 'restaurant']) {
      const query = mode === 'stt' || mode === 'full'
        ? new File(['voice'], 'question.webm', { type: 'audio/webm' }) : 'Cuéntame más.';
      const fetchMock = t.mock.method(globalThis, 'fetch', async (_url, { body }) => {
        assert.equal(body.get('language'), 'ES');
        assert.equal(body.get('request_type'), requestType ?? null);
        return mode === 'tts' || mode === 'full'
          ? new Response('wav', { headers: { 'content-type': 'audio/wav' } })
          : Response.json({ text: 'Respuesta del guía' });
      });
      await sendChatRequest({ ...chat, mode, requestType, query, language: 'ES' });
      fetchMock.mock.restore();
    }
  }
});

test('Spanish validation and server errors retain useful details', async (t) => {
  await assert.rejects(sendChatRequest({ ...chat, language: 'ES', query: '' }), /Escribe una pregunta/);
  t.mock.method(globalThis, 'fetch', async () =>
    Response.json({ detail: 'Provider unavailable' }, { status: 503 }));
  await assert.rejects(sendChatRequest({ ...chat, language: 'ES' }),
    /La consulta falló \(HTTP 503\): Provider unavailable/);
});

test('invalid chat fields are rejected before a request is sent', async (t) => {
  const fetchMock = t.mock.method(globalThis, 'fetch');
  for (const invalid of [
    { stop: ' ' }, { requestType: 'unknown' }, { mode: 'unknown' }, { language: 'FR' },
    { query: ' ' }, { mode: 'stt', query: 'text' },
    { mode: 'full', query: new Blob([], { type: 'audio/wav' }) },
    { mode: 'full', query: new Blob(['audio'], { type: 'text/plain' }) },
    { query: new Blob(['audio'], { type: 'audio/wav' }) }
  ]) {
    await assert.rejects(sendChatRequest({ ...chat, ...invalid }));
  }
  assert.equal(fetchMock.mock.callCount(), 0);
});

test('audio size limit is inclusive at 14,000,000 bytes', async (t) => {
  const fetchMock = t.mock.method(globalThis, 'fetch', async () => Response.json({ text: 'Answer' }));
  const audio = new Blob([new Uint8Array(14_000_000)], { type: 'audio/wav' });
  await sendChatRequest({ ...chat, mode: 'stt', query: audio });
  const oversized = new Blob([audio, 'x'], { type: 'audio/wav' });
  await assert.rejects(
    sendChatRequest({ ...chat, mode: 'stt', query: oversized }), /14,000,000/
  );
  assert.equal(fetchMock.mock.callCount(), 1);
});

test('surfaces JSON detail, validation issues, and plain-text server errors', async (t) => {
  for (const [response, expected] of [
    [Response.json({ detail: 'Audio required' }, { status: 422 }), /HTTP 422.*Audio required/],
    [Response.json({ detail: [{ loc: ['body', 'stop'], msg: 'Field required' }] },
      { status: 422 }), /body.stop: Field required/],
    [new Response('Internal Server Error', { status: 500 }), /HTTP 500.*Internal Server Error/]
  ]) {
    const fetchMock = t.mock.method(globalThis, 'fetch', async () => response);
    await assert.rejects(sendChatRequest(chat), expected);
    fetchMock.mock.restore();
  }
});

test('rejects malformed or empty text and audio replies', async (t) => {
  for (const [mode, response] of [
    ['text', Response.json({ text: '' })],
    ['text', Response.json({ text: 42 })],
    ['text', Response.json({})],
    ['text', new Response('not json')],
    ['tts', Response.json({ text: 'Wrong response type' })],
    ['tts', new Response('', { headers: { 'content-type': 'audio/wav' } })]
  ]) {
    const fetchMock = t.mock.method(globalThis, 'fetch', async () => response);
    await assert.rejects(sendChatRequest({ ...chat, mode }));
    fetchMock.mock.restore();
  }
});

test('chat cancellation and network failures propagate', async (t) => {
  const controller = new AbortController();
  controller.abort();
  const fetchMock = t.mock.method(globalThis, 'fetch', async (_url, { signal }) => {
    signal.throwIfAborted();
    throw new TypeError('Network unavailable');
  });
  await assert.rejects(sendChatRequest(chat, controller.signal), { name: 'AbortError' });
  await assert.rejects(sendChatRequest(chat), /Network unavailable/);
  fetchMock.mock.restore();
});

test('chat requests have a two-minute timeout', async (t) => {
  const controller = new AbortController();
  controller.abort(new DOMException('Chat timed out', 'TimeoutError'));
  t.mock.method(AbortSignal, 'timeout', (milliseconds) => {
    assert.equal(milliseconds, 120_000);
    return controller.signal;
  });
  t.mock.method(globalThis, 'fetch', async (_url, { signal }) => signal.throwIfAborted());
  await assert.rejects(sendChatRequest(chat), { name: 'TimeoutError' });
});
