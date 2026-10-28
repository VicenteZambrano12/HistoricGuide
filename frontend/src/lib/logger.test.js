import assert from 'node:assert/strict';
import { test } from 'node:test';
import { createCorrelationId, createLogger, getErrorContext, setErrorContext } from './logger.js';

function capture(production) {
  const records = [];
  const output = Object.fromEntries(['debug', 'info', 'warn', 'error'].map((level) => [
    level, (prefix, record) => records.push({ level, prefix, record })
  ]));
  return { log: createLogger({ production, output }), records };
}

test('logger emits timestamped structured records at all development levels', () => {
  const { log, records } = capture(false);
  for (const level of ['debug', 'info', 'warn', 'error']) log[level]('test.event', { count: 2 });
  assert.deepEqual(records.map(({ record }) => record.level), ['DEBUG', 'INFO', 'WARN', 'ERROR']);
  for (const { prefix, record } of records) {
    assert.ok(Number.isFinite(Date.parse(record.timestamp)));
    assert.equal(record.event, 'test.event');
    assert.equal(record.context.count, 2);
    assert.ok(prefix.includes(record.timestamp));
  }
});

test('production suppresses debug and info before serializing context', () => {
  const { log, records } = capture(true);
  const context = { get error() { throw new Error('Must not inspect suppressed data'); } };
  log.debug('test.debug', context);
  log.info('test.info', context);
  log.warn('test.warn');
  log.error('test.error');
  assert.deepEqual(records.map(({ level }) => level), ['warn', 'error']);
});

test('logger redacts sensitive metadata, URL queries, credentials, and token strings', () => {
  const { log, records } = capture(false);
  log.error('test.redaction', {
    authorization: 'Bearer secret',
    query: 'private conversation',
    body: { content: 'private body' },
    audio: new Blob(['private audio']),
    nested: { password: 'private-password', api_key: 'private-key' },
    error: new Error('Failed at https://user:pass@example.com/api/chat?token=secret#private'),
    detail: 'Bearer abc123 token=abc123'
  });
  const serialized = JSON.stringify(records);
  for (const secret of ['private conversation', 'private body', 'private audio', 'private-password', 'private-key', 'user:pass', 'token=secret', '#private', 'abc123']) {
    assert.equal(serialized.includes(secret), false, secret);
  }
  assert.equal(records[0].record.context.nested.password, '[redacted]');
});

test('error metadata preserves stack, cause, and per-error correlation without mutation', () => {
  const { log, records } = capture(false);
  const cause = new TypeError('Network unavailable');
  const error = Object.freeze(new Error('Request failed', { cause }));
  setErrorContext(error, { correlationId: 'trace-1', requestId: 'request-1' });
  log.error('test.failure', { error });
  const { context } = records[0].record;
  assert.equal(context.correlationId, 'trace-1');
  assert.match(context.error.stack, /Request failed/);
  assert.equal(context.error.cause.name, 'TypeError');
  assert.equal(context.error.requestId, 'request-1');
  assert.deepEqual(getErrorContext(new Error('Other request')), {});
  assert.deepEqual(getErrorContext(null), {});
});

test('serialization bounds cycles, nested metadata, and unsupported browser objects', () => {
  const { log, records } = capture(false);
  const cyclic = {};
  cyclic.self = cyclic;
  log.warn('test.cycle', { cyclic, resource: new URL('https://example.com/?secret=hidden') });
  assert.equal(records[0].record.context.cyclic.self, '[circular]');
  assert.equal(records[0].record.context.resource, '[unsupported object]');
});

test('generated correlation IDs are unique UUIDs accepted by FastAPI', () => {
  const ids = Array.from({ length: 100 }, createCorrelationId);
  assert.equal(new Set(ids).size, ids.length);
  for (const id of ids) assert.match(id, /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/);
});

test('hostile metadata cannot crash error handling and produces an explicit logger error', () => {
  const { log, records } = capture(false);
  const hostile = { get field() { throw new Error('Getter failed'); } };
  assert.doesNotThrow(() => log.error('test.hostile', { detail: hostile }));
  assert.equal(records[0].record.event, 'logger.serialization_failed');
  assert.equal(records[0].record.level, 'ERROR');
  assert.doesNotThrow(() => log.error('test.after_hostile', { reason: 'Still available' }));
  assert.equal(records[1].record.event, 'test.after_hostile');
});
