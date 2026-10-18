export const THEME_STORAGE_KEY = 'plinius-theme';

export function getSavedTheme(storage) {
  try {
    return storage.getItem(THEME_STORAGE_KEY) === 'light' ? 'light' : 'dark';
  } catch (error) {
    console.warn('Unable to read the saved theme; using dark mode.', error);
    return 'dark';
  }
}

export function saveTheme(theme, storage) {
  try {
    storage.setItem(THEME_STORAGE_KEY, theme);
  } catch (error) {
    console.warn('Unable to save the theme; it will only apply to this visit.', error);
  }
}
