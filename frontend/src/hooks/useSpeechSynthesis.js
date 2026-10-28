import { useState, useEffect, useCallback } from 'react';
import { logger } from '../lib/logger.js';

export function useSpeechSynthesis(language = 'en') {
  const [audioEnabled, setAudioEnabled] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);

  const stopSpeech = useCallback(() => {
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      window.speechSynthesis.cancel();
    }
    setIsSpeaking(false);
  }, []);

  const speakText = useCallback(
    (text) => {
      if (typeof window === 'undefined' || !('speechSynthesis' in window)) {
        return;
      }

      window.speechSynthesis.cancel();

      if (!audioEnabled) {
        setIsSpeaking(true);
        const simulatedDuration = Math.min(4500, Math.max(1800, text.length * 16));
        const timer = setTimeout(() => setIsSpeaking(false), simulatedDuration);
        return () => clearTimeout(timer);
      }

      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = language === 'es' ? 'es-ES' : 'en-GB';
      utterance.rate = 1.02;
      utterance.pitch = 0.95;

      utterance.onstart = () => setIsSpeaking(true);
      utterance.onend = () => setIsSpeaking(false);
      utterance.onerror = (event) => {
        setIsSpeaking(false);
        if (!['canceled', 'interrupted'].includes(event.error)) {
          logger.warn('voice.synthesis_failed', { reason: event.error });
        }
      };

      window.speechSynthesis.speak(utterance);
    },
    [audioEnabled, language]
  );

  const toggleAudio = useCallback(() => {
    setAudioEnabled((prev) => {
      const next = !prev;
      if (!next && typeof window !== 'undefined' && 'speechSynthesis' in window) {
        window.speechSynthesis.cancel();
        setIsSpeaking(false);
      }
      return next;
    });
  }, []);

  useEffect(() => {
    return () => {
      if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
        window.speechSynthesis.cancel();
      }
    };
  }, []);

  return {
    audioEnabled,
    isSpeaking,
    speakText,
    stopSpeech,
    toggleAudio
  };
}
