import { apiRequest } from './http.js';

const REASONS = new Set([
  'unreachable', 'collection_missing', 'collection_empty',
  'collection_incompatible', 'configuration', 'startup_failed'
]);

export class DemoStartupError extends Error {
  constructor(reason) {
    super(`Demo preparation failed: ${reason}`);
    this.reason = reason;
  }
}

async function requestDemo(action, signal) {
  return apiRequest(`/api/demo/${action}`, {
    method: action === 'start' ? 'POST' : 'GET',
    signal: AbortSignal.any([signal, AbortSignal.timeout(action === 'start' ? 15000 : 10000)]),
    cache: 'no-store'
  }, async (response) => {
    if (![200, 202, 503].includes(response.status)) {
      throw new DemoStartupError('startup_failed');
    }
    const data = await response.json();
    const valid = (
      response.status === 200 && data?.status === 'ready' && data.retryable === false
    ) || (
      response.status === 202 && data?.status === 'starting' && data.retryable === true
    ) || (
      response.status === 503 && REASONS.has(data?.reason)
      && ((data.status === 'waiting' && data.retryable === true)
        || (data.status === 'unavailable' && data.retryable === false))
    );
    if (!valid) throw new DemoStartupError('startup_failed');
    return data;
  });
}

function delay(milliseconds, signal) {
  signal.throwIfAborted();
  return new Promise((resolve, reject) => {
    const abort = () => {
      clearTimeout(timer);
      reject(signal.reason);
    };
    const timer = setTimeout(() => {
      signal.removeEventListener('abort', abort);
      resolve();
    }, milliseconds);
    signal.addEventListener('abort', abort, { once: true });
  });
}

export async function prepareDemo(signal, onState) {
  const deadline = AbortSignal.timeout(180000);
  const boundedSignal = AbortSignal.any([signal, deadline]);
  let nextStart = 0;
  try {
    while (true) {
      boundedSignal.throwIfAborted();
      onState('checking');
      try {
        const readiness = await requestDemo('ready', boundedSignal);
        if (readiness.status === 'ready') return;
        if (!readiness.retryable) throw new DemoStartupError(readiness.reason);
        onState('starting');
        if (Date.now() >= nextStart) {
          const startup = await requestDemo('start', boundedSignal);
          if (startup.status === 'ready') return;
          if (!startup.retryable) throw new DemoStartupError(startup.reason);
          nextStart = Date.now() + 15000;
        }
      } catch (error) {
        if (!(error instanceof TypeError) && error.name !== 'TimeoutError') throw error;
        onState('starting');
      }
      await delay(5000, boundedSignal);
    }
  } catch (error) {
    if (deadline.aborted && !signal.aborted) throw new DemoStartupError('startup_timeout');
    throw error;
  }
}
