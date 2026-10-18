import { useTour } from '../../store/TourContext';
import './Navbar.css';

export function Navbar({ theme, onToggleTheme }) {
  const {
    audioEnabled,
    toggleAudio,
    isChatPending,
    isWalking,
    isVoiceRecording,
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
          <span lang="en">EN</span>
          <span aria-hidden="true">/</span>
          <span lang="es">ES</span>
          <span aria-hidden="true">({language.toUpperCase()})</span>
        </button>
        <button
          type="button"
          className="navbar__btn"
          aria-label={t('lightMode')}
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
          disabled={isChatPending || isWalking || isVoiceRecording}
        >
          {t(audioEnabled ? 'voiceOn' : 'voiceOff')}
        </button>

        <button type="button" className="navbar__btn" onClick={resetTour}>
          {t('resetWalk')}
        </button>
      </div>
    </header>
  );
}
