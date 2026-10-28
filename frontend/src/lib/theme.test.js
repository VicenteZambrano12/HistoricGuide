import assert from 'node:assert/strict';
import { test } from 'node:test';
import { getSavedTheme, saveTheme, THEME_STORAGE_KEY } from './theme.js';

test('restores valid themes and defaults to dark for missing or invalid values', () => {
  for (const [saved, expected] of [
    ['light', 'light'], ['dark', 'dark'], [null, 'dark'], ['invalid', 'dark']
  ]) {
    assert.equal(getSavedTheme({
      getItem(key) {
        assert.equal(key, THEME_STORAGE_KEY);
        return saved;
      }
    }), expected);
  }
});

test('persists both theme choices', () => {
  for (const theme of ['light', 'dark']) {
    const writes = [];
    saveTheme(theme, { setItem: (...args) => writes.push(args) });
    assert.deepEqual(writes, [[THEME_STORAGE_KEY, theme]]);
  }
});

test('storage failures warn without preventing theme changes', (t) => {
  const warnings = [];
  t.mock.method(console, 'warn', (...args) => warnings.push(args));
  const error = new Error('Storage blocked');
  const storage = {
    getItem() { throw error; },
    setItem() { throw error; }
  };
  assert.equal(getSavedTheme(storage), 'dark');
  assert.doesNotThrow(() => saveTheme('light', storage));
  assert.equal(warnings.length, 2);
  assert.equal(warnings[0][1], error);
  assert.equal(warnings[1][1], error);
});
