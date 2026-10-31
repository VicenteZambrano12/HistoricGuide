import { createContext, useContext, useState, useCallback, useEffect, useRef, useMemo } from 'react';
import { ROME_STOPS } from '../lib/romeStopsData';
import { buildRagTelemetry } from '../lib/ragEngine';
import { useSpeechSynthesis } from '../hooks/useSpeechSynthesis';
import { useGpsSimulation } from '../hooks/useGpsSimulation';
import { useDemoAvailability } from '../hooks/useDemoAvailability';
import { sendChatRequest } from '../lib/api';
import { TRANSLATIONS, getTranslator, getSavedLanguage, saveLanguage } from '../i18n/translations';
import { getErrorContext, logger } from '../lib/logger.js';

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
  const { demoState, isDemoReady, ensureDemoReady } = useDemoAvailability();

  useEffect(() => () => chatRequest.current?.abort(), []);

  const [messages, setMessages] = useState([]);

  const [ragTelemetry, setRagTelemetry] = useState(() =>
    buildRagTelemetry(ROME_STOPS[0], 'OVERVIEW')
  );

  const { audioEnabled, isSpeaking, stopSpeech, toggleAudio } =
    useSpeechSynthesis(language);

  const {
    gpsPosition,
    setGpsPosition,
    isWalking,
    walkProgress,
    cancelWalkSimulation,
    startWalkSimulation
  } = useGpsSimulation(ROME_STOPS[0].coords);

  const isInteractionBusy = isChatPending || isWalking || isVoiceRecording;

  const appendMessage = useCallback((sender, text, tag = '', audio = null, audioMode = null) => {
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
        autoPlay: Boolean(audio),
        isNarration: audioMode === 'tts',
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

  const sendChat = useCallback(async ({
    query, mode = audioEnabled ? 'tts' : 'text', requestType, stop = currentStop.apiStop
  }) => {
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
      if (!await ensureDemoReady() || controller.signal.aborted) return false;
      const result = await sendChatRequest({
        stop,
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
        appendMessage('Plinius', { key: 'audioAnswer' }, `BACKEND / ${language.toUpperCase()}`, result.audio, mode);
      } else {
        appendMessage('Plinius', result.text, `BACKEND / ${language.toUpperCase()}`);
      }
      return true;
    } catch (error) {
      if (!controller.signal.aborted) {
        const { correlationId } = getErrorContext(error);
        if (!correlationId) logger.warn('chat.input_failed', { error });
        const message = error instanceof TypeError || error.name === 'TimeoutError' || error instanceof SyntaxError
          ? t('chatConnectionError', { detail: error.message }) : error.message;
        setChatError(correlationId
          ? `${message} ${t('errorReference', { reference: correlationId })}`
          : message);
      }
      return false;
    } finally {
      if (chatRequest.current === controller) {
        chatRequest.current = null;
        setIsChatPending(false);
        setChatProgress([]);
      }
    }
  }, [currentStop, appendMessage, audioEnabled, stopSpeech, language, t, ensureDemoReady]);

  const approachRef = useRef(null);
  useEffect(() => {
    approachRef.current = (targetIdx) => sendChat({
      stop: stops[targetIdx].apiStop,
      query: t('approachingQuery', { name: stops[targetIdx].name }),
      requestType: 'historic'
    });
  }, [sendChat, stops, t]);

  const walkToStopIndex = useCallback(
    (targetIdx) => {
      if (isInteractionBusy || chatRequest.current) return;
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
        void approachRef.current(targetIdx);
      });
    },
    [gpsPosition, currentStop, stopSpeech, appendMessage, startWalkSimulation, cancelChat, stops, isInteractionBusy]
  );

  const confirmArrivalAtStop = useCallback(() => {
    if (isInteractionBusy || chatRequest.current) return;
    setGpsPosition(currentStop.coords);
    setTourPhase('ARRIVED_OVERVIEW');
    setRagTelemetry(buildRagTelemetry(currentStop, 'OVERVIEW'));

    void sendChat({
      query: t('arrivalQuery', { name: currentStop.name }),
      requestType: 'historic'
    });
  }, [currentStop, setGpsPosition, sendChat, isInteractionBusy, t]);

  const askHistoricalRag = useCallback(() => {
    if (isInteractionBusy || chatRequest.current) return;
    setTourPhase('HISTORICAL_RAG');
    setRagTelemetry(buildRagTelemetry(currentStop, 'HISTORICAL'));

    void sendChat({
      query: t('historyQuery'),
      requestType: 'historic'
    });
  }, [currentStop, sendChat, t, isInteractionBusy]);

  const askGastroRag = useCallback((query = t('foodQuery')) => {
    if (isInteractionBusy || chatRequest.current) return;
    setTourPhase('GASTRO_RAG');
    setRagTelemetry(buildRagTelemetry(currentStop, 'GASTRO'));

    void sendChat({
      query,
      requestType: 'restaurant'
    });
  }, [currentStop, sendChat, t, isInteractionBusy]);

  const advanceToNextStop = useCallback(() => {
    if (isInteractionBusy || chatRequest.current) return;
    const nextIdx = currentStopIndex + 1;
    if (nextIdx < ROME_STOPS.length) {
      walkToStopIndex(nextIdx);
    } else {
      cancelChat();
      setTourPhase('TOUR_COMPLETED');
      void sendChat({ query: t('farewellQuery'), requestType: 'historic' });
    }
  }, [currentStopIndex, walkToStopIndex, cancelChat, sendChat, t, isInteractionBusy]);

  const finishTour = useCallback(() => {
    if (isInteractionBusy || chatRequest.current) return;
    cancelChat();
    cancelWalkSimulation();
    setTourPhase('TOUR_COMPLETED');
    void sendChat({
      query: t('finishQuery', { name: currentStop.name }),
      requestType: 'historic'
    });
  }, [currentStop, sendChat, cancelChat, cancelWalkSimulation, t, isInteractionBusy]);

  const resetTour = useCallback(() => {
    cancelChat();
    cancelWalkSimulation();
    stopSpeech();
    setCurrentStopIndex(0);
    setGpsPosition(ROME_STOPS[0].coords);
    setTourPhase('READY_TO_ARRIVE');
    setRagTelemetry(buildRagTelemetry(ROME_STOPS[0], 'OVERVIEW'));
    setMessages([]);
  }, [stopSpeech, setGpsPosition, cancelChat, cancelWalkSimulation]);

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
        isInteractionBusy,
        demoState,
        isDemoReady,
        ensureDemoReady,
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
