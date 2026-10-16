import React from 'react';
import { useTour } from '../../store/TourContext';
import './Navbar.css';

export function Navbar() {
  const {
    activePage,
    setActivePage,
    layoutMode,
    setLayoutMode,
    audioEnabled,
    toggleAudio,
    resetTour
  } = useTour();

  return (
    <header className="navbar">
      <div className="navbar__brand">
        <div className="navbar__seal">SPQR</div>
        <div>
          <div className="navbar__title">
            AURELIUS
            <span className="navbar__badge">VOICE AI + QDRANT RAG</span>
          </div>
          <p className="navbar__subtitle">
            Peripatetic Ancient Rome Historian • Republic &amp; Empire Interactive Portfolio Demo
          </p>
        </div>
      </div>

      <div className="navbar__controls">
        <button
          type="button"
          className={`navbar__btn ${activePage === 'WORKSTATION' ? 'navbar__btn--active' : ''}`}
          onClick={() => setActivePage('WORKSTATION')}
        >
          🧭 Live Rome Tour
        </button>

        <button
          type="button"
          className={`navbar__btn ${activePage === 'ARCHITECTURE' ? 'navbar__btn--active' : ''}`}
          onClick={() => setActivePage('ARCHITECTURE')}
        >
          🖼️ UI Screens &amp; Architecture
        </button>

        {activePage === 'WORKSTATION' && (
          <>
            <button
              type="button"
              className={`navbar__btn ${layoutMode === 'SPLIT' ? 'navbar__btn--active' : ''}`}
              onClick={() => setLayoutMode(layoutMode === 'SPLIT' ? 'MOBILE' : 'SPLIT')}
            >
              {layoutMode === 'SPLIT' ? '📱 Switch to Mobile Frame' : '🖥️ Switch to Split Workstation'}
            </button>

            <button
              type="button"
              className={`navbar__btn ${audioEnabled ? 'navbar__btn--audio-on' : ''}`}
              onClick={toggleAudio}
            >
              {audioEnabled ? '🔊 Real Voice TTS: ON' : '🔇 Enable Real Voice TTS'}
            </button>

            <button type="button" className="navbar__btn" onClick={resetTour}>
              ↺ Reset Walk
            </button>
          </>
        )}
      </div>
    </header>
  );
}
