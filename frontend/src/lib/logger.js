const LEVELS = { DEBUG: 10, INFO: 20, WARN: 30, ERROR: 40 };
const errorContexts = new WeakMap();
const SENSITIVE_KEY = /authorization|cookie|password|secret|token|api[-_]?key|query|body|audio|transcript/i;

export function createCorrelationId() {
  if (globalThis.crypto.randomUUID) return globalThis.crypto.randomUUID();
  const bytes = globalThis.crypto.getRandomValues(new Uint8Array(16));
  bytes[6] = (bytes[6] & 15) | 64;
  bytes[8] = (bytes[8] & 63) | 128;
  const hex = Array.from(bytes, (byte) => byte.toString(16).padStart(2, '0')).join('');
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}

export function setErrorContext(error, context) {
  if (error !== null && (typeof error === 'object' || typeof error === 'function')) {
    errorContexts.set(error, { ...getErrorContext(error), ...context });
  }
}

export function getErrorContext(error) {
  return error !== null && (typeof error === 'object' || typeof error === 'function')
    ? errorContexts.get(error) ?? {}
    : {};
}

function safeText(value) {
  return value
    .replace(/https?:\/\/[^\s)]+/g, (url) => {
      try {
        const parsed = new URL(url);
        return `${parsed.origin}${parsed.pathname}`;
      } catch {
        return '[invalid URL]';
      }
    })
    .replace(/\bBearer\s+\S+/gi, 'Bearer [redacted]')
    .replace(/\b(password|secret|token|api[-_]?key)\s*[=:]\s*["']?[^"'\s,;]+/gi, '$1=[redacted]')
    .slice(0, 8000);
}

function sanitize(value, seen = new WeakSet(), depth = 0) {
  if (typeof value === 'string') return safeText(value);
  if (value === null || typeof value === 'number' || typeof value === 'boolean') return value;
  if (typeof value !== 'object') return `[${typeof value}]`;
  if (seen.has(value)) return '[circular]';
  if (depth >= 6) return '[truncated]';
  seen.add(value);
  if (value instanceof Error || value instanceof DOMException) {
    return sanitize({
      name: value.name,
      message: value.message,
      stack: value.stack,
      ...getErrorContext(value),
      ...(value.cause === undefined ? {} : { cause: value.cause })
    }, seen, depth + 1);
  }
  if (Array.isArray(value)) return value.slice(0, 50).map((item) => sanitize(item, seen, depth + 1));
  if (Object.getPrototypeOf(value) !== Object.prototype && Object.getPrototypeOf(value) !== null) {
    return '[unsupported object]';
  }
  return Object.fromEntries(Object.entries(value).slice(0, 50).map(([key, item]) => [
    key, SENSITIVE_KEY.test(key) ? '[redacted]' : sanitize(item, seen, depth + 1)
  ]));
}

export function createLogger({ production = import.meta.env?.PROD === true, output = console } = {}) {
  const minimum = production ? LEVELS.WARN : LEVELS.DEBUG;
  return Object.fromEntries(Object.entries(LEVELS).map(([level, priority]) => [
    level.toLowerCase(),
    (event, context = {}) => {
      if (priority < minimum) return;
      let record;
      try {
        record = {
          timestamp: new Date().toISOString(),
          level,
          event: safeText(event),
          context: sanitize({ ...getErrorContext(context.error), ...context })
        };
      } catch {
        record = {
          timestamp: new Date().toISOString(),
          level: 'ERROR',
          event: 'logger.serialization_failed',
          context: { message: 'Log metadata could not be safely serialized.' }
        };
      }
      output[record.level.toLowerCase()](
        `[Plinius] ${record.timestamp} ${record.level} ${record.event}`, record
      );
    }
  ]));
}

export const logger = createLogger();
