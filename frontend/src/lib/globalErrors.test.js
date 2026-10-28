import assert from 'node:assert/strict';
import { test } from 'node:test';
import { installGlobalErrorHandlers } from './globalErrors.js';
import { logger, setErrorContext } from './logger.js';

test('global handlers capture uncaught errors and promise rejections without suppressing browser behavior', (t) => {
  const target = new EventTarget();
  const errors = [];
  t.mock.method(logger, 'error', (event, context) => errors.push({ event, context }));
  const cleanup = installGlobalErrorHandlers(target);
  t.after(cleanup);
  assert.equal(installGlobalErrorHandlers(target), cleanup);
  const error = new Error('Uncaught failure');
  setErrorContext(error, { correlationId: 'test-trace' });
  const event = new Event('error', { cancelable: true });
  Object.assign(event, { error, lineno: 12, colno: 4 });
  target.dispatchEvent(event);
  const rejection = new Event('unhandledrejection', { cancelable: true });
  Object.assign(rejection, { reason: 'Rejected without Error' });
  target.dispatchEvent(rejection);
  assert.deepEqual(errors.map(({ event: name }) => name), ['browser.uncaught_error', 'browser.unhandled_rejection']);
  assert.equal(errors[0].context.error, error);
  assert.equal(errors[0].context.line, 12);
  assert.equal(errors[1].context.error, 'Rejected without Error');
  assert.equal(event.defaultPrevented, false);
  assert.equal(rejection.defaultPrevented, false);
  cleanup();
  target.dispatchEvent(event);
  assert.equal(errors.length, 2);
});

test('script errors without Error objects remain visible', (t) => {
  const target = new EventTarget();
  const errors = [];
  t.mock.method(logger, 'error', (_event, context) => errors.push(context));
  const cleanup = installGlobalErrorHandlers(target);
  t.after(cleanup);
  const event = new Event('error');
  Object.assign(event, { message: 'Script error.' });
  target.dispatchEvent(event);
  assert.equal(errors[0].error.message, 'Script error.');
});

test('cleanup allows reinstalling without old disposers removing new handlers', (t) => {
  const target = new EventTarget();
  const errorLog = t.mock.method(logger, 'error', () => {});
  const cleanup = installGlobalErrorHandlers(target);
  cleanup();
  const secondCleanup = installGlobalErrorHandlers(target);
  t.after(secondCleanup);
  cleanup();
  const event = new Event('error');
  Object.assign(event, { error: new Error('After reinstall') });
  target.dispatchEvent(event);
  assert.equal(errorLog.mock.callCount(), 1);
});
