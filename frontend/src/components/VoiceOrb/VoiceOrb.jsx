import React from 'react';
import { useTour } from '../../store/TourContext';
import './VoiceOrb.css';

export function VoiceOrb() {
  const { isSpeaking, isWalking, tourPhase } = useTour();

  const getStatusLabel = () => {
    if (isWalking) return 'GPS WALKING SIMULATION ACTIVE...';
    if (isSpeaking) return 'SYNTHESIZING VOICE NARRATION...';
    if (tourPhase === 'READY_TO_ARRIVE') return 'AWAITING ARRIVAL CONFIRMATION';
    return 'LISTENING FOR TOURIST VOICE INTENT';
  };

  return (
    <div className="voice-orb">
      <div className="voice-orb__left">
        <div className={`voice-orb__core ${isSpeaking ? 'voice-orb__core--speaking' : ''}`}>
          🎙️
        </div>
        <div className="voice-orb__meta">
          <span className="voice-orb__speaker">AURELIUS // VOICE AI HISTORIAN</span>
          <span className="voice-orb__status">{getStatusLabel()}</span>
        </div>
      </div>

      <div className={`voice-orb__bars ${isSpeaking ? 'voice-orb__bars--active' : ''}`}>
        <span className="voice-orb__bar" />
        <span className="voice-orb__bar" />
        <span className="voice-orb__bar" />
        <span className="voice-orb__bar" />
        <span className="voice-orb__bar" />
      </div>
    </div>
  );
}
