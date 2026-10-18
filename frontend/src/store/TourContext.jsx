import { createContext, useContext, useState, useCallback, useEffect, useRef, useMemo } from 'react';
import { ROME_STOPS } from '../lib/romeStopsData';
import { buildRagTelemetry } from '../lib/ragEngine';
import { useSpeechSynthesis } from '../hooks/useSpeechSynthesis';
import { useGpsSimulation } from '../hooks/useGpsSimulation';
import { sendChatRequest } from '../lib/api';
import { TRANSLATIONS, getTranslator, getSavedLanguage, saveLanguage } from '../i18n/translations';

const TourContext = createContext(null);

export function TourProvider({ children }) {
  const [language, setLanguage] = useState(() => getSavedLanguage({
    getItem: (key) => window.localStorage.getItem(key)
  }));
  const t = useMemo(() => getTranslator(language), [language]);
  const stops = useMemo(() => ROME_STOPS.map((stop) => ({
    ...stop,
    ...TRANSLATIONS[language].stops[stop.id]
  })), [language]);
  const resolveMessage = useCallback((text) => typeof text === 'string' ? text : t(text.key, {
    ...TRANSLATIONS[language].stops[text.stopId],
    ...text.values
  }), [language, t]);

  useEffect(() => {
    document.documentElement.lang = language;
  }, [language]);

  const [layoutMode, setLayoutMode] = useState('SPLIT'); // 'SPLIT' | 'MOBILE'
  const [currentStopIndex, setCurrentStopIndex] = useState(0);
  // Phases: 'WALKING_TO_STOP' | 'READY_TO_ARRIVE' | 'ARRIVED_OVERVIEW' | 'HISTORICAL_RAG' | 'GASTRO_RAG' | 'TOUR_COMPLETED'
  const [tourPhase, setTourPhase] = useState('READY_TO_ARRIVE');

  const currentStop = stops[currentStopIndex];
  const chatRequest = useRef(null);
  const [isChatPending, setIsChatPending] = useState(false);
  const [chatProgress, setChatProgress] = useState([]);
  const [chatSources, setChatSources] = useState([]);
  const [chatError, setChatError] = useState(null);
  const [chatSessionId, setChatSessionId] = useState(0);
  const [isVoiceRecording, setIsVoiceRecording] = useState(false);

  useEffect(() => () => chatRequest.current?.abort(), []);

  const [messages, setMessages] = useState([
    {
      id: 'init-msg',
      sender: 'Plinius',
      tag: 'PERIPATETIC GPS GUIDE',
      timestamp: '09:30 AM',
      text: { key: 'initialMessage', stopId: ROME_STOPS[0].id }
    }
  ]);

  const [ragTelemetry, setRagTelemetry] = useState(() =>
    buildRagTelemetry(ROME_STOPS[0], 'OVERVIEW')
  );

  const { audioEnabled, isSpeaking, speakText, stopSpeech, toggleAudio: toggleSpeechAudio } =
    useSpeechSynthesis(language);
  const narrationRef = useRef({ speakText, resolveMessage });
  useEffect(() => {
    narrationRef.current = { speakText, resolveMessage };
  }, [speakText, resolveMessage]);

  const {
    gpsPosition,
    setGpsPosition,
    isWalking,
    walkProgress,
    startWalkSimulation
  } = useGpsSimulation(ROME_STOPS[0].coords);

  const appendMessage = useCallback((sender, text, tag = '', audio = null, autoPlay = false) => {
    const now = new Date().toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit'
    });
    setMessages((prev) => [
      ...prev,
      {
        id: `msg_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
        sender,
        tag,
        audio,
        autoPlay,
        timestamp: now,
        text
      }
    ]);
  }, []);

  const cancelChat = useCallback(() => {
    chatRequest.current?.abort();
    chatRequest.current = null;
    setIsChatPending(false);
    setChatProgress([]);
    setChatSources([]);
    setChatError(null);
    setChatSessionId((previous) => previous + 1);
  }, []);

  const toggleLanguage = useCallback(() => {
    const nextLanguage = language === 'en' ? 'es' : 'en';
    cancelChat();
    stopSpeech();
    setLanguage(nextLanguage);
    saveLanguage(nextLanguage, {
      setItem: (key, value) => window.localStorage.setItem(key, value)
    });
  }, [language, cancelChat, stopSpeech]);

  const sendChat = useCallback(async ({ query, mode = audioEnabled ? 'tts' : 'text', requestType }) => {
    if (chatRequest.current) return false;
    const controller = new AbortController();
    chatRequest.current = controller;
    setIsChatPending(true);
    setChatProgress([]);
    setChatSources([]);
    setChatError(null);
    stopSpeech();
    appendMessage(
      'USER',
      typeof query === 'string' ? query : {
        key: 'audioQuestion', values: { name: query?.name || t('recordingName') }
      },
      `${(requestType || 'auto').toUpperCase()} / ${mode.toUpperCase()} / ${language.toUpperCase()}`
    );

    try {
      const result = await sendChatRequest({
        stop: currentStop.apiStop,
        requestType,
        mode,
        query,
        language: language.toUpperCase(),
        onProgress: (step) => {
          if (chatRequest.current === controller && !controller.signal.aborted) {
            setChatProgress((previous) => previous.includes(step) ? previous : [...previous, step]);
          }
        }
      }, controller.signal);
      if (controller.signal.aborted) return false;
      setChatSources(result.sources ?? []);
      if (result.audio) {
        appendMessage('Plinius', { key: 'audioAnswer' }, `BACKEND / ${language.toUpperCase()}`, result.audio, mode === 'tts');
      } else {
        appendMessage('Plinius', result.text, `BACKEND / ${language.toUpperCase()}`);
      }
      return true;
    } catch (error) {
      if (!controller.signal.aborted) {
        setChatError(error instanceof TypeError || error.name === 'TimeoutError' || error instanceof SyntaxError
          ? t('chatConnectionError', { detail: error.message }) : error.message);
      }
      return false;
    } finally {
      if (chatRequest.current === controller) {
        chatRequest.current = null;
        setIsChatPending(false);
        setChatProgress([]);
      }
    }
  }, [currentStop, appendMessage, audioEnabled, stopSpeech, language, t]);

  const walkToStopIndex = useCallback(
    (targetIdx) => {
      if (targetIdx < 0 || targetIdx >= ROME_STOPS.length) return;
      const targetStop = stops[targetIdx];
      const fromCoords = gpsPosition || currentStop.coords;

      cancelChat();
      stopSpeech();
      setCurrentStopIndex(targetIdx);
      setTourPhase('WALKING_TO_STOP');

      appendMessage(
        'USER',
        { key: 'walkMessage', stopId: targetStop.id, values: { order: targetStop.order } },
        'VOICE INTENT'
      );

      startWalkSimulation(fromCoords, targetStop.coords, 2000, () => {
        setTourPhase('READY_TO_ARRIVE');
        const arrivalPrompt = { key: 'approachingMessage', stopId: targetStop.id };
        appendMessage('Plinius', arrivalPrompt, 'GPS PROXIMITY ALERT');
        const narration = narrationRef.current;
        narration.speakText(narration.resolveMessage(arrivalPrompt));
      });
    },
    [gpsPosition, currentStop, stopSpeech, appendMessage, startWalkSimulation, cancelChat, stops]
  );

  const confirmArrivalAtStop = useCallback(() => {
    if (chatRequest.current || isWalking || isVoiceRecording) return;
    setGpsPosition(currentStop.coords);
    setTourPhase('ARRIVED_OVERVIEW');
    setRagTelemetry(buildRagTelemetry(currentStop, 'OVERVIEW'));

    void sendChat({
      query: t('arrivalQuery', { name: currentStop.name }),
      requestType: 'historic'
    });
  }, [currentStop, setGpsPosition, sendChat, isWalking, isVoiceRecording, t]);

  const toggleAudio = useCallback(() => {
    if (chatRequest.current || isWalking || isVoiceRecording) return;
    toggleSpeechAudio();
  }, [toggleSpeechAudio, isWalking, isVoiceRecording]);

  const askHistoricalRag = useCallback(() => {
    if (chatRequest.current) return;
    setTourPhase('HISTORICAL_RAG');
    setRagTelemetry(buildRagTelemetry(currentStop, 'HISTORICAL'));

    void sendChat({
      query: t('historyQuery'),
      requestType: 'historic'
    });
  }, [currentStop, sendChat, t]);

  const askGastroRag = useCallback((query = t('foodQuery')) => {
    if (chatRequest.current) return;
    setTourPhase('GASTRO_RAG');
    setRagTelemetry(buildRagTelemetry(currentStop, 'GASTRO'));

    void sendChat({
      query,
      requestType: 'restaurant'
    });
  }, [currentStop, sendChat, t]);

  const advanceToNextStop = useCallback(() => {
    const nextIdx = currentStopIndex + 1;
    if (nextIdx < ROME_STOPS.length) {
      walkToStopIndex(nextIdx);
    } else {
      cancelChat();
      setTourPhase('TOUR_COMPLETED');
      const farewell = { key: 'farewell' };
      appendMessage('Plinius', farewell, 'TOUR COMPLETED');
      speakText(resolveMessage(farewell));
    }
  }, [currentStopIndex, walkToStopIndex, appendMessage, speakText, cancelChat, resolveMessage]);

  const finishTour = useCallback(() => {
    cancelChat();
    setTourPhase('TOUR_COMPLETED');
    const summaryText = { key: 'finishMessage', stopId: currentStop.id };
    appendMessage('USER', { key: 'finishIntent' }, 'VOICE INTENT');
    appendMessage('Plinius', summaryText, 'SESSION ENDED');
    speakText(resolveMessage(summaryText));
  }, [currentStop, appendMessage, speakText, cancelChat, resolveMessage]);

  const resetTour = useCallback(() => {
    cancelChat();
    stopSpeech();
    setCurrentStopIndex(0);
    setGpsPosition(ROME_STOPS[0].coords);
    setTourPhase('READY_TO_ARRIVE');
    setRagTelemetry(buildRagTelemetry(ROME_STOPS[0], 'OVERVIEW'));
    setMessages([
      {
        id: `reset_${Date.now()}`,
        sender: 'Plinius',
        tag: 'PERIPATETIC GPS GUIDE',
        timestamp: '09:30 AM',
        text: { key: 'resetMessage', stopId: ROME_STOPS[0].id }
      }
    ]);
  }, [stopSpeech, setGpsPosition, cancelChat]);

  return (
    <TourContext.Provider
      value={{
        stops,
        language,
        t,
        resolveMessage,
        toggleLanguage,
        layoutMode,
        setLayoutMode,
        currentStopIndex,
        currentStop,
        tourPhase,
        messages,
        sendChat,
        isChatPending,
        chatProgress,
        chatSources,
        chatError,
        chatSessionId,
        isVoiceRecording,
        setIsVoiceRecording,
        ragTelemetry,
        gpsPosition,
        isWalking,
        walkProgress,
        audioEnabled,
        isSpeaking,
        toggleAudio,
        stopSpeech,
        walkToStopIndex,
        confirmArrivalAtStop,
        askHistoricalRag,
        askGastroRag,
        advanceToNextStop,
        finishTour,
        resetTour
      }}
    >
      {children}
    </TourContext.Provider>
  );
}

export function useTour() {
  const context = useContext(TourContext);
  if (!context) {
    throw new Error('useTour must be used within a TourProvider');
  }
  return context;
}
