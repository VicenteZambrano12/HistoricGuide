import { useTour } from '../../store/TourContext';
import './VoiceOrb.css';

export function VoiceOrb() {
  const { isSpeaking, isWalking, tourPhase, isChatPending, isVoiceRecording } = useTour();

  const getStatusLabel = () => {
    if (isWalking) return 'GPS WALKING SIMULATION ACTIVE...';
    if (isVoiceRecording) return 'MICROPHONE ACTIVE...';
    if (isChatPending) return 'WAITING FOR BACKEND GUIDE...';
    if (isSpeaking) return 'SYNTHESIZING VOICE NARRATION...';
    if (tourPhase === 'READY_TO_ARRIVE') return 'AWAITING ARRIVAL CONFIRMATION';
    return 'READY FOR A QUESTION OR VOICE MESSAGE';
  };

  return (
    <div className="voice-orb">
      <div className="voice-orb__left">
        <div className={`voice-orb__core ${isSpeaking ? 'voice-orb__core--speaking' : ''}`}>
          🎙️
        </div>
        <div className="voice-orb__meta">
          <span className="voice-orb__speaker">Plinius // VOICE AI HISTORIAN</span>
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
