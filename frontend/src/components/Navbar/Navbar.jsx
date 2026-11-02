import { useTour } from '../../store/TourContext';
import { ChatIcon } from '../ChatIcon/ChatIcon';
import './Navbar.css';

export function Navbar({ theme, onToggleTheme }) {
  const {
    audioEnabled,
    toggleAudio,
    resetTour,
    language,
    toggleLanguage,
    t
  } = useTour();

  return (
    <header className="navbar">
      <div className="navbar__brand">
        <img className="navbar__logo" src="/logo.jpeg" alt={t('logoAlt')} width="40" height="40" />
        <div>
          <div className="navbar__title">
            Plinius
          </div>
          <p className="navbar__subtitle">
            {t('appTagline')}
          </p>
        </div>
      </div>

      <div className="navbar__controls">
        <button
          type="button"
          className="navbar__btn"
          aria-label={t('languageToggle')}
          title={t('languageToggle')}
          onClick={toggleLanguage}
        >
          <span lang="en" className={language === 'en' ? 'navbar__language--selected' : ''}>EN</span>
          <span aria-hidden="true">/</span>
          <span lang="es" className={language === 'es' ? 'navbar__language--selected' : ''}>ES</span>
        </button>
        <button
          type="button"
          className="navbar__btn"
          aria-label={t(theme === 'dark' ? 'switchToLight' : 'switchToDark')}
          aria-pressed={theme === 'light'}
          title={t(theme === 'dark' ? 'switchToLight' : 'switchToDark')}
          onClick={onToggleTheme}
        >
          <span aria-hidden="true">{theme === 'dark' ? '☀' : '☾'}</span>
          {t(theme === 'dark' ? 'lightMode' : 'darkMode')}
        </button>

        <button
          type="button"
          className={`navbar__btn ${audioEnabled ? 'navbar__btn--audio-on' : ''}`}
          onClick={toggleAudio}
          aria-pressed={audioEnabled}
        >
          <ChatIcon name={audioEnabled ? 'volume' : 'muted'} />
          {t(audioEnabled ? 'voiceOn' : 'voiceOff')}
        </button>

        <button type="button" className="navbar__btn" onClick={resetTour}>
          {t('resetWalk')}
        </button>
      </div>
    </header>
  );
}
