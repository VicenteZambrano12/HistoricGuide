import assert from 'node:assert/strict';
import { beforeEach, test } from 'node:test';
import { setImmediate } from 'node:timers';
import { prepareDemo } from './demo.js';
import { logger } from './logger.js';

const ready = () => Response.json({ status: 'ready', reason: null, retryable: false });
const waiting = () => Response.json(
  { status: 'waiting', reason: 'unreachable', retryable: true }, { status: 503 }
);
const starting = () => Response.json(
  { status: 'starting', reason: null, retryable: true }, { status: 202 }
);
const flush = () => new Promise((resolve) => setImmediate(resolve));

beforeEach((t) => {
  for (const level of ['debug', 'info', 'warn', 'error']) t.mock.method(logger, level, () => {});
});

test('a ready guide never calls the starter or keeps polling', async (t) => {
  const fetch = t.mock.method(globalThis, 'fetch', async (path, options) => {
    assert.equal(path, '/api/demo/ready');
    assert.equal(options.method, 'GET');
    assert.equal(options.cache, 'no-store');
    return ready();
  });
  await prepareDemo(new AbortController().signal, () => {});
  await flush();
  assert.equal(fetch.mock.callCount(), 1);
});

test('opens a sleeping demo, checks collection readiness, and stops when ready', async (t) => {
  t.mock.timers.enable({ apis: ['setTimeout', 'Date'] });
  const paths = [];
  const states = [];
  t.mock.method(globalThis, 'fetch', async (path, options) => {
    paths.push(path);
    if (path.endsWith('/start')) {
      assert.equal(options.method, 'POST');
      return starting();
    }
    return paths.length === 1 ? waiting() : ready();
  });
  const pending = prepareDemo(new AbortController().signal, (status) => states.push(status));
  await flush();
  assert.deepEqual(paths, ['/api/demo/ready', '/api/demo/start']);
  t.mock.timers.tick(5000);
  await pending;
  assert.deepEqual(paths, ['/api/demo/ready', '/api/demo/start', '/api/demo/ready']);
  assert.ok(states.includes('starting'));
  t.mock.timers.tick(300000);
  await flush();
  assert.equal(paths.length, 3);
});

test('retries start races and stopping transitions with a fifteen-second cooldown', async (t) => {
  t.mock.timers.enable({ apis: ['setTimeout', 'Date'] });
  let starts = 0;
  let reads = 0;
  t.mock.method(globalThis, 'fetch', async (path) => {
    if (path.endsWith('/start')) {
      starts += 1;
      return starts === 1
        ? Response.json({ status: 'waiting', reason: 'startup_failed', retryable: true }, { status: 503 })
        : starting();
    }
    reads += 1;
    return reads === 5 ? ready() : waiting();
  });
  const pending = prepareDemo(new AbortController().signal, () => {});
  await flush();
  for (let index = 0; index < 4; index += 1) {
    t.mock.timers.tick(5000);
    await flush();
  }
  await pending;
  assert.equal(starts, 2);
  assert.equal(reads, 5);
});

test('missing or incompatible documents fail without repeatedly waking the VM', async (t) => {
  for (const reason of ['collection_missing', 'collection_empty', 'collection_incompatible', 'configuration']) {
    const fetch = t.mock.method(globalThis, 'fetch', async () => Response.json(
      { status: 'unavailable', reason, retryable: false }, { status: 503 }
    ));
    await assert.rejects(prepareDemo(new AbortController().signal, () => {}), { reason });
    assert.equal(fetch.mock.callCount(), 1);
    fetch.mock.restore();
  }
});

test('invalid API shapes are explicit failures, not readiness', async (t) => {
  for (const data of [{}, { status: 'ready' }, { status: 'ready', retryable: true }]) {
    const fetch = t.mock.method(globalThis, 'fetch', async () => Response.json(data));
    await assert.rejects(prepareDemo(new AbortController().signal, () => {}), { reason: 'startup_failed' });
    fetch.mock.restore();
  }
});

test('cancellation stops startup polling and suppresses further calls', async (t) => {
  t.mock.timers.enable({ apis: ['setTimeout', 'Date'] });
  const controller = new AbortController();
  const fetch = t.mock.method(globalThis, 'fetch', async (path) =>
    path.endsWith('/ready') ? waiting() : starting()
  );
  const pending = prepareDemo(controller.signal, () => {});
  await flush();
  controller.abort();
  await assert.rejects(pending, { name: 'AbortError' });
  t.mock.timers.tick(300000);
  assert.equal(fetch.mock.callCount(), 2);
});

test('startup has a hard three-minute bound and exposes a retryable user action', async (t) => {
  t.mock.timers.enable({ apis: ['setTimeout', 'Date'] });
  const deadline = new AbortController();
  const original = AbortSignal.timeout;
  t.mock.method(AbortSignal, 'timeout', (milliseconds) => {
    if (milliseconds === 180000) return deadline.signal;
    return original(milliseconds);
  });
  t.mock.method(globalThis, 'fetch', async (path) => path.endsWith('/ready') ? waiting() : starting());
  const pending = prepareDemo(new AbortController().signal, () => {});
  await flush();
  deadline.abort(new DOMException('Timed out', 'TimeoutError'));
  await assert.rejects(pending, { reason: 'startup_timeout' });
});

test('a new user request rechecks readiness and wakes a VM that shut down while idle', async (t) => {
  t.mock.timers.enable({ apis: ['setTimeout', 'Date'] });
  let calls = 0;
  const paths = [];
  t.mock.method(globalThis, 'fetch', async (path) => {
    paths.push(path);
    calls += 1;
    return calls === 2 ? waiting() : path.endsWith('/start') ? starting() : ready();
  });
  await prepareDemo(new AbortController().signal, () => {});
  const nextRequest = prepareDemo(new AbortController().signal, () => {});
  await flush();
  t.mock.timers.tick(5000);
  await nextRequest;
  assert.deepEqual(paths, [
    '/api/demo/ready', '/api/demo/ready', '/api/demo/start', '/api/demo/ready'
  ]);
});
