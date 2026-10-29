import { useEffect, useRef } from 'react';
import { useTour } from '../../../store/TourContext';
import { ChatComposer } from '../ChatComposer/ChatComposer';
import { AudioAnswer } from '../ChatComposer/AudioAnswer';
import { ChatIcon } from '../../../components/ChatIcon/ChatIcon';
import './HistorianVoicePanel.css';

const WAVE_HEIGHTS = [10, 18, 12, 26, 34, 20, 14, 30, 22, 38, 28, 16, 24, 34, 18, 10, 22, 30, 40, 26, 16, 28, 36, 20, 12, 24, 32, 18, 26, 14, 20, 10];

export function HistorianVoicePanel() {
  const {
    messages, isChatPending, chatProgress, chatError, chatSessionId,
    demoState, ensureDemoReady, t, resolveMessage
  } = useTour();
  const transcriptRef = useRef(null);

  useEffect(() => {
    const transcript = transcriptRef.current;
    transcript?.scrollTo({
      top: transcript.scrollHeight,
      behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth'
    });
  }, [messages]);

  return (
    <aside className="voice-panel" aria-labelledby="guide-title">
      <header className="voice-panel__header">
        <span className="voice-panel__avatar" aria-hidden="true"><ChatIcon name="history" /></span>
        <div>
          <h2 id="guide-title">{t('yourGuide')}</h2>
          <p>{t('guideDescription')}</p>
        </div>
      </header>
      {demoState.status !== 'ready' && (
        <div className="voice-panel__startup">
          <p role={demoState.status === 'error' ? 'alert' : 'status'}>
            {demoState.status === 'error'
              ? t(`demoError_${demoState.reason}`)
              : t('demoStarting')}
          </p>
          {demoState.status === 'error' && (
            <button type="button" onClick={() => { void ensureDemoReady(); }}>
              {t('demoRetry')}
            </button>
          )}
        </div>
      )}
      <div className="voice-panel__transcript" ref={transcriptRef} role="log" aria-label={t('conversation')} aria-relevant="additions" tabIndex={0}>
        {messages.length === 0 && (
          <div className="voice-panel__empty">
            <ChatIcon name="message" />
            <h3>{t('guideEmptyTitle')}</h3>
            <p>{t('guideEmptyBody')}</p>
          </div>
        )}
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`voice-panel__msg ${
              msg.sender === 'Plinius' ? 'voice-panel__msg--ai' : 'voice-panel__msg--user'
            } ${msg.text?.key === 'audioQuestion' ? 'voice-panel__msg--voice' : ''}`}
          >
            <div className="voice-panel__msg-header">
              <span>
                {msg.sender === 'Plinius' ? 'Plinius' : t('you')}
              </span>
              <span>{msg.timestamp}</span>
            </div>
            {msg.text?.key === 'audioQuestion' ? (
              <div className="voice-message">
                <span className="voice-message__icon"><ChatIcon name="microphone" /></span>
                <div className="voice-message__body">
                  <div className="voice-message__bars" aria-hidden="true">
                    {WAVE_HEIGHTS.map((height, index) => (
                      <span key={index} style={{ height: `${height}px` }} />
                    ))}
                  </div>
                  <span className="voice-message__label">{t('voiceMessage')}</span>
                </div>
              </div>
            ) : (
              <p className="voice-panel__msg-text">{resolveMessage(msg.text)}</p>
            )}
            {msg.audio && <AudioAnswer audio={msg.audio} autoPlay={msg.autoPlay} />}
          </div>
        ))}
      </div>

      {isChatPending && (
        <div className="voice-panel__progress">
          <p className="voice-panel__progress-title">{t('pipelineProgress')}</p>
          {chatProgress.length > 0 && (
            <ol className="voice-panel__steps" role="status" aria-live="polite" aria-atomic="false">
              {chatProgress.map((step, index) => (
                <li key={step} className={index === chatProgress.length - 1 ? 'is-active' : ''}>
                  <span aria-hidden="true">{index === chatProgress.length - 1 ? '>' : '+'}</span>
                  {t(`progress_${step}`)}
                </li>
              ))}
            </ol>
          )}
          {chatProgress.length === 0 && <p role="status">{t('progress_sending')}</p>}
        </div>
      )}
      {chatError && <p className="voice-panel__error" role="alert">{chatError}</p>}
      <ChatComposer key={chatSessionId} />
    </aside>
  );
}
