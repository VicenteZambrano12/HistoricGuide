import en from './en.json' with { type: 'json' };
import es from './es.json' with { type: 'json' };

export const TRANSLATIONS = { en, es };
export const LANGUAGE_STORAGE_KEY = 'plinius-language';

export function getTranslator(language) {
  const dictionary = TRANSLATIONS[language];
  if (!dictionary) throw new Error(`Unsupported language: ${language}`);
  return (key, values = {}) => {
    const text = dictionary[key];
    if (typeof text !== 'string') throw new Error(`Missing translation: ${language}.${key}`);
    return text.replace(/\{(\w+)\}/g, (_, name) => {
      if (!(name in values)) throw new Error(`Missing translation value: ${key}.${name}`);
      return String(values[name]);
    });
  };
}

export function getSavedLanguage(storage) {
  try {
    return storage.getItem(LANGUAGE_STORAGE_KEY) === 'es' ? 'es' : 'en';
  } catch (error) {
    console.warn('Unable to read the saved language; using English.', error);
    return 'en';
  }
}

export function saveLanguage(language, storage) {
  if (!Object.hasOwn(TRANSLATIONS, language)) throw new Error(`Unsupported language: ${language}`);
  try {
    storage.setItem(LANGUAGE_STORAGE_KEY, language);
  } catch (error) {
    console.warn('Unable to save the language; it will only apply to this visit.', error);
  }
}
