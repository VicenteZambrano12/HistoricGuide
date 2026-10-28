import { logger } from './logger.js';

const installations = new WeakMap();

export function installGlobalErrorHandlers(target = window) {
  if (installations.has(target)) return installations.get(target);

  const onError = (event) => {
    if (event.target && event.target !== target && !event.error) {
      logger.warn('browser.resource_failed', { tag: event.target.tagName });
      return;
    }
    logger.error('browser.uncaught_error', {
      error: event.error ?? new Error(event.message || 'Script error'),
      line: event.lineno,
      column: event.colno
    });
  };
  const onRejection = (event) => {
    logger.error('browser.unhandled_rejection', { error: event.reason });
  };

  target.addEventListener('error', onError, { capture: true });
  target.addEventListener('unhandledrejection', onRejection);
  const cleanup = () => {
    if (installations.get(target) !== cleanup) return;
    target.removeEventListener('error', onError, { capture: true });
    target.removeEventListener('unhandledrejection', onRejection);
    installations.delete(target);
  };
  installations.set(target, cleanup);
  return cleanup;
}
