import { createCorrelationId, logger, setErrorContext } from './logger.js';

const TRACE_ID = /^[a-z0-9._:-]{1,128}$/i;

function responseId(response, header) {
  const value = response.headers.get(header);
  if (value === null) return null;
  if (TRACE_ID.test(value)) return value;
  logger.warn('http.invalid_trace_header', { header });
  return null;
}

export async function apiRequest(path, options, consume) {
  const correlationId = createCorrelationId();
  const context = {
    method: options.method ?? 'GET',
    route: path.split(/[?#]/)[0],
    correlationId,
    requestId: correlationId
  };
  const headers = new Headers(options.headers);
  headers.set('X-Correlation-ID', correlationId);
  // FastAPI's request logger currently consumes X-Request-ID.
  headers.set('X-Request-ID', correlationId);
  const started = performance.now();
  const duration = () => Math.round((performance.now() - started) * 1000) / 1000;
  logger.debug('http.request_started', context);

  try {
    const response = await fetch(path, { ...options, headers });
    const serverCorrelationId = responseId(response, 'X-Correlation-ID');
    const serverRequestId = responseId(response, 'X-Request-ID');
    context.clientCorrelationId = correlationId;
    context.correlationId = serverCorrelationId ?? serverRequestId ?? correlationId;
    context.requestId = serverRequestId ?? context.correlationId;
    context.status = response.status;
    logger.info('http.response_received', { ...context, durationMs: duration() });
    const result = await consume(response);
    if (result?.audio) setErrorContext(result.audio, context);
    logger.info('http.request_completed', { ...context, durationMs: duration() });
    return result;
  } catch (error) {
    const cancelled = options.signal?.aborted && options.signal.reason?.name !== 'TimeoutError';
    const metadata = { ...context, durationMs: duration() };
    if (!cancelled) setErrorContext(error, metadata);
    if (cancelled) {
      logger.debug('http.request_cancelled', metadata);
    } else {
      logger.error('http.request_failed', { ...metadata, error });
    }
    throw error;
  }
}
