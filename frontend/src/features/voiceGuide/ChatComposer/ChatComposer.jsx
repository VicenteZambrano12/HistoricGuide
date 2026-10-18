import { useState } from 'react';
import { useTour } from '../../../store/TourContext';
import { useVoiceRecorder } from '../../../hooks/useVoiceRecorder';
import { ActionPromptChips } from '../ActionPromptChips/ActionPromptChips';
import { ChatIcon } from '../../../components/ChatIcon/ChatIcon';

export function ChatComposer() {
  const { sendChat, isChatPending, isWalking, setIsVoiceRecording, stopSpeech, t } = useTour();
  const [query, setQuery] = useState('');
  const recorder = useVoiceRecorder((audio) => {
    void sendChat({ query: audio, mode: 'full' });
  }, setIsVoiceRecording);
  const recordingActive = recorder.status !== 'idle';
  const disabled = isChatPending || isWalking;

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (await sendChat({ query })) setQuery('');
  };

  return (
    <>
      <form className="chat-composer" onSubmit={handleSubmit}>
        <label htmlFor="chat-query">
          <span className="chat-composer__label">
            <ChatIcon name="message" />
            {t('message')}
          </span>
          <textarea
            id="chat-query"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder={t('queryPlaceholder')}
            rows={2}
            required
            disabled={disabled || recordingActive}
          />
        </label>
        <div className="chat-composer__actions">
          <button
            type="button"
            className={`chat-composer__microphone ${recorder.status === 'recording' ? 'chat-composer__recording' : ''}`}
            aria-label={t(recorder.status === 'recording' ? 'stopRecording' : 'recordVoice')}
            aria-pressed={recorder.status === 'recording'}
            disabled={disabled || recorder.status === 'requesting' || recorder.status === 'stopping'}
            onClick={() => {
              if (recorder.status === 'recording') {
                recorder.stop();
              } else {
                stopSpeech();
                void recorder.start();
              }
            }}
          >
            <ChatIcon name={recorder.status === 'recording' ? 'stop' : 'microphone'} />
            <span>{t(recorder.status === 'recording' ? 'stopAndSend' : 'microphone')}</span>
          </button>
          <button
            type="submit"
            className="chat-composer__send"
            disabled={disabled || recordingActive || !query.trim()}
          >
            <span>{t(isChatPending ? 'sending' : 'send')}</span>
            <ChatIcon name="send" />
          </button>
        </div>
        {recordingActive && (
          <p role="status">
            {t(recorder.status === 'requesting' ? 'waitingForMicrophone'
              : recorder.status === 'recording' ? 'recording' : 'preparingVoice')}
          </p>
        )}
        {recorder.error && (
          <p className="voice-panel__error" role="alert">
            {t(recorder.error.key, recorder.error.values)}
          </p>
        )}
      </form>
      <ActionPromptChips disabled={recordingActive} />
    </>
  );
}
