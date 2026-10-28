import { useEffect, useRef, useState } from 'react';
import { useTour } from '../../../store/TourContext';
import { ChatIcon } from '../../../components/ChatIcon/ChatIcon';
import { getErrorContext, logger } from '../../../lib/logger.js';
import './AudioAnswer.css';

function formatTime(seconds) {
  const value = Number.isFinite(seconds) ? Math.max(0, Math.floor(seconds)) : 0;
  return `${Math.floor(value / 60)}:${String(value % 60).padStart(2, '0')}`;
}

export function AudioAnswer({ audio, autoPlay = false }) {
  const playerRef = useRef(null);
  const [playbackError, setPlaybackError] = useState(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(1);
  const [muted, setMuted] = useState(false);
  const { stopSpeech, audioEnabled, isChatPending, isWalking, tourPhase, isVoiceRecording, language, t } = useTour();
  const autoplayAttempted = useRef(false);
  const playbackBlocked = isChatPending || isWalking || isVoiceRecording || tourPhase === 'TOUR_COMPLETED';

  useEffect(() => {
    const player = playerRef.current;
    const url = URL.createObjectURL(audio);
    player.src = url;
    return () => {
      player.pause();
      player.removeAttribute('src');
      player.load();
      URL.revokeObjectURL(url);
    };
  }, [audio]);

  useEffect(() => {
    if (playbackBlocked || (autoPlay && !audioEnabled)) {
      playerRef.current.pause();
    }
  }, [playbackBlocked, autoPlay, audioEnabled]);

  useEffect(() => {
    playerRef.current.pause();
  }, [language]);

  useEffect(() => {
    if (!autoPlay || !audioEnabled || playbackBlocked || autoplayAttempted.current) return;
    autoplayAttempted.current = true;
    let cancelled = false;
    playerRef.current.play().catch((error) => {
      if (!cancelled && error.name !== 'AbortError') {
        logger.warn('audio.autoplay_failed', { ...getErrorContext(audio), error });
        setPlaybackError('playbackError');
      }
    });
    return () => { cancelled = true; };
  }, [autoPlay, audioEnabled, playbackBlocked, audio]);

  const togglePlayback = async () => {
    const player = playerRef.current;
    if (!player.paused) {
      player.pause();
      return;
    }
    setPlaybackError(null);
    try {
      await player.play();
    } catch (error) {
      if (error.name !== 'AbortError') {
        logger.warn('audio.playback_failed', { ...getErrorContext(audio), error });
        setPlaybackError('playbackError');
      }
    }
  };

  return (
    <div className={`audio-answer ${isPlaying ? 'audio-answer--playing' : ''}`} role="group" aria-label={t('guideAudio')}>
      <audio
        ref={playerRef}
        hidden
        preload="metadata"
        onPlay={() => {
          stopSpeech();
          setIsPlaying(true);
        }}
        onPause={() => setIsPlaying(false)}
        onEnded={() => setIsPlaying(false)}
        onTimeUpdate={(event) => setCurrentTime(event.currentTarget.currentTime)}
        onDurationChange={(event) => {
          const value = event.currentTarget.duration;
          setDuration(Number.isFinite(value) ? value : 0);
        }}
        onError={(event) => {
          logger.error('audio.media_failed', { ...getErrorContext(audio), code: event.currentTarget.error?.code });
          setPlaybackError('playbackError');
        }}
      />
      <button
        type="button"
        className="audio-answer__orb"
        aria-label={t(isPlaying ? 'pauseAudio' : 'playAudio')}
        aria-pressed={isPlaying}
        onClick={togglePlayback}
        disabled={isWalking || isVoiceRecording || tourPhase === 'TOUR_COMPLETED'}
      >
        <span className="audio-answer__sphere" aria-hidden="true" />
        <span className="audio-answer__orb-icon"><ChatIcon name={isPlaying ? 'pause' : 'play'} /></span>
      </button>
      <div className="audio-answer__body">
        <span className="audio-answer__eyebrow">{t('voiceAnswer')}</span>
        <span className="audio-answer__status" role="status">
          {t(isPlaying ? 'audioPlaying' : 'audioReady')}
        </span>
        <div className="audio-answer__timeline">
          <input
            type="range"
            aria-label={t('audioProgress')}
            aria-valuetext={`${formatTime(currentTime)} / ${formatTime(duration)}`}
            min="0"
            max={duration || 1}
            step="0.1"
            value={Math.min(currentTime, duration || 1)}
            disabled={!duration}
            onChange={(event) => {
              const value = Number(event.target.value);
              playerRef.current.currentTime = value;
              setCurrentTime(value);
            }}
          />
          <span className="audio-answer__time">{formatTime(currentTime)} / {formatTime(duration)}</span>
        </div>
        <div className="audio-answer__volume">
          <button
            type="button"
            aria-label={t(muted || volume === 0 ? 'unmuteAudio' : 'muteAudio')}
            onClick={() => {
              const nextMuted = !(muted || volume === 0);
              playerRef.current.muted = nextMuted;
              setMuted(nextMuted);
              if (!nextMuted && volume === 0) {
                playerRef.current.volume = 1;
                setVolume(1);
              }
            }}
          >
            <ChatIcon name={muted || volume === 0 ? 'muted' : 'volume'} />
          </button>
          <input
            type="range"
            aria-label={t('audioVolume')}
            min="0"
            max="1"
            step="0.01"
            value={muted ? 0 : volume}
            onChange={(event) => {
              const value = Number(event.target.value);
              playerRef.current.volume = value;
              playerRef.current.muted = false;
              setVolume(value);
              setMuted(false);
            }}
          />
        </div>
      </div>
      {playbackError && <p className="voice-panel__error audio-answer__error" role="alert">{t(playbackError)}</p>}
    </div>
  );
}
