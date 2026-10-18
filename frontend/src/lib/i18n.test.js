import assert from 'node:assert/strict';
import { test } from 'node:test';
import {
  TRANSLATIONS, getTranslator, getSavedLanguage, saveLanguage, LANGUAGE_STORAGE_KEY
} from '../i18n/translations.js';
import { ROME_STOPS } from './romeStopsData.js';

function leafEntries(object, prefix = '') {
  return Object.entries(object).flatMap(([key, value]) => {
    const path = prefix ? `${prefix}.${key}` : key;
    return typeof value === 'string' ? [[path, value]] : leafEntries(value, path);
  });
}

test('English and Spanish dictionaries have matching nonempty strings and placeholders', () => {
  const en = leafEntries(TRANSLATIONS.en);
  const es = new Map(leafEntries(TRANSLATIONS.es));
  assert.deepEqual(en.map(([key]) => key).sort(), [...es.keys()].sort());
  for (const [key, text] of en) {
    assert.ok(text.trim(), key);
    assert.ok(es.get(key).trim(), key);
    assert.deepEqual(
      [...text.matchAll(/\{(\w+)\}/g)].map((match) => match[1]).sort(),
      [...es.get(key).matchAll(/\{(\w+)\}/g)].map((match) => match[1]).sort(),
      key
    );
  }
});

test('all tour stop display fields are translated and English preserves existing labels', () => {
  for (const stop of ROME_STOPS) {
    for (const language of ['en', 'es']) {
      const translated = TRANSLATIONS[language].stops[stop.id];
      assert.ok(translated, stop.id);
      for (const key of ['name', 'subtitle', 'era', 'periodTag']) {
        assert.ok(translated[key].trim(), `${language}.${stop.id}.${key}`);
        if (language === 'en') assert.equal(translated[key], stop[key]);
      }
    }
  }
});

test('interpolates dictionary strings and rejects missing keys, values, and unsupported languages', () => {
  const t = getTranslator('es');
  assert.equal(t('currentStop', { order: 2, era: 'República' }),
    'PARADA ACTUAL #2 • República');
  assert.equal(getTranslator('en')('send'), 'Send');
  assert.equal(t('send'), 'Enviar');
  assert.throws(() => t('unknown'), /Missing translation/);
  assert.throws(() => t('currentStop'), /Missing translation value/);
  assert.throws(() => getTranslator('fr'), /Unsupported language/);
});

test('defaults to English and restores a valid saved Spanish preference', () => {
  for (const [saved, expected] of [
    [null, 'en'], ['en', 'en'], ['es', 'es'], ['fr', 'en'], ['ES', 'en']
  ]) {
    assert.equal(getSavedLanguage({
      getItem(key) {
        assert.equal(key, LANGUAGE_STORAGE_KEY);
        return saved;
      }
    }), expected);
  }
});

test('persists both languages and rejects unsupported language writes', () => {
  const writes = [];
  const storage = { setItem: (...args) => writes.push(args) };
  saveLanguage('en', storage);
  saveLanguage('es', storage);
  assert.deepEqual(writes, [[LANGUAGE_STORAGE_KEY, 'en'], [LANGUAGE_STORAGE_KEY, 'es']]);
  assert.throws(() => saveLanguage('fr', storage), /Unsupported language/);
});

test('blocked storage warns but does not prevent language changes', (t) => {
  const warnings = [];
  t.mock.method(console, 'warn', (...args) => warnings.push(args));
  const error = new Error('Storage blocked');
  const storage = {
    getItem() { throw error; },
    setItem() { throw error; }
  };
  assert.equal(getSavedLanguage(storage), 'en');
  assert.doesNotThrow(() => saveLanguage('es', storage));
  assert.equal(warnings.length, 2);
  assert.equal(warnings[0][1], error);
  assert.equal(warnings[1][1], error);
});
