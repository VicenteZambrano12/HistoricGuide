export const THEME_STORAGE_KEY = 'plinius-theme';

export function getSavedTheme(storage) {
  try {
    return storage.getItem(THEME_STORAGE_KEY) === 'light' ? 'light' : 'dark';
  } catch (error) {
    logger.warn('preferences.theme_read_failed', { error });
    return 'dark';
  }
}

export function saveTheme(theme, storage) {
  try {
    storage.setItem(THEME_STORAGE_KEY, theme);
  } catch (error) {
    logger.warn('preferences.theme_save_failed', { error });
  }
}
import { logger } from './logger.js';
