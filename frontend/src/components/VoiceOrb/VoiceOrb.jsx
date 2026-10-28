import { useTour } from '../../store/TourContext';
import { ChatIcon } from '../ChatIcon/ChatIcon';
import './VoiceOrb.css';

export function VoiceOrb() {
  const { isSpeaking, isWalking, tourPhase, isChatPending, isVoiceRecording, t } = useTour();

  const getStatusLabel = () => {
    if (isWalking) return t('guideWalking');
    if (isVoiceRecording) return t('guideRecording');
    if (isChatPending) return t('guideWaiting');
    if (isSpeaking) return t('guideSpeaking');
    if (tourPhase === 'READY_TO_ARRIVE') return t('guideArrival');
    return t('guideReady');
  };

  return (
    <div className="voice-orb">
      <div className="voice-orb__left">
        <div className={`voice-orb__core ${isSpeaking ? 'voice-orb__core--speaking' : ''}`} aria-hidden="true">
          <ChatIcon name="microphone" />
        </div>
        <div className="voice-orb__meta">
          <span className="voice-orb__speaker">{t('yourGuide')}</span>
          <span className="voice-orb__status" role="status">{getStatusLabel()}</span>
        </div>
      </div>

      <div className={`voice-orb__bars ${isSpeaking ? 'voice-orb__bars--active' : ''}`} aria-hidden="true">
        <span className="voice-orb__bar" />
        <span className="voice-orb__bar" />
        <span className="voice-orb__bar" />
        <span className="voice-orb__bar" />
        <span className="voice-orb__bar" />
      </div>
    </div>
  );
}
