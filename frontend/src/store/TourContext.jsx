import React, { createContext, useContext, useState, useCallback } from 'react';
import { ROME_STOPS } from '../lib/romeStopsData';
import { buildRagTelemetry } from '../lib/ragEngine';
import { useSpeechSynthesis } from '../hooks/useSpeechSynthesis';
import { useGpsSimulation } from '../hooks/useGpsSimulation';

const TourContext = createContext(null);

export function TourProvider({ children }) {
  const [activePage, setActivePage] = useState('WORKSTATION'); // 'WORKSTATION' | 'ARCHITECTURE'
  const [layoutMode, setLayoutMode] = useState('SPLIT'); // 'SPLIT' | 'MOBILE'
  const [currentStopIndex, setCurrentStopIndex] = useState(0);
  // Phases: 'WALKING_TO_STOP' | 'READY_TO_ARRIVE' | 'ARRIVED_OVERVIEW' | 'HISTORICAL_RAG' | 'GASTRO_RAG' | 'TOUR_COMPLETED'
  const [tourPhase, setTourPhase] = useState('READY_TO_ARRIVE');

  const currentStop = ROME_STOPS[currentStopIndex];

  const [messages, setMessages] = useState([
    {
      id: 'init-msg',
      sender: 'AURELIUS',
      tag: 'PERIPATETIC GPS GUIDE',
      timestamp: '09:30 AM',
      text: `Salve! We are walking through the Campus Martius toward Stop #1: ${ROME_STOPS[0].name} (${ROME_STOPS[0].era}). Tap "Simulate 'I Have Arrived'" as soon as you reach the monument perimeter.`
    }
  ]);

  const [ragTelemetry, setRagTelemetry] = useState(() =>
    buildRagTelemetry(ROME_STOPS[0], 'OVERVIEW')
  );

  const { audioEnabled, isSpeaking, speakText, stopSpeech, toggleAudio } =
    useSpeechSynthesis();

  const {
    gpsPosition,
    setGpsPosition,
    isWalking,
    walkProgress,
    startWalkSimulation
  } = useGpsSimulation(ROME_STOPS[0].coords);

  const appendMessage = useCallback((sender, text, tag = '') => {
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
        timestamp: now,
        text
      }
    ]);
  }, []);

  const walkToStopIndex = useCallback(
    (targetIdx) => {
      if (targetIdx < 0 || targetIdx >= ROME_STOPS.length) return;
      const targetStop = ROME_STOPS[targetIdx];
      const fromCoords = gpsPosition || currentStop.coords;

      stopSpeech();
      setCurrentStopIndex(targetIdx);
      setTourPhase('WALKING_TO_STOP');

      appendMessage(
        'USER',
        `🎙️ "Let's walk to Stop #${targetStop.order}: ${targetStop.name}."`,
        'VOICE INTENT'
      );

      startWalkSimulation(fromCoords, targetStop.coords, 2000, () => {
        setTourPhase('READY_TO_ARRIVE');
        const arrivalPrompt = `You are now approaching ${targetStop.name} (${targetStop.era}). Let me know when you've arrived at the monument to begin the overview.`;
        appendMessage('AURELIUS', arrivalPrompt, 'GPS PROXIMITY ALERT');
        speakText(arrivalPrompt);
      });
    },
    [gpsPosition, currentStop, stopSpeech, appendMessage, startWalkSimulation, speakText]
  );

  const confirmArrivalAtStop = useCallback(() => {
    setGpsPosition(currentStop.coords);
    setTourPhase('ARRIVED_OVERVIEW');
    setRagTelemetry(buildRagTelemetry(currentStop, 'OVERVIEW'));

    appendMessage(
      'USER',
      `🎙️ "I've arrived at ${currentStop.name}."`,
      'GPS ARRIVAL TRIGGER'
    );
    appendMessage(
      'AURELIUS',
      currentStop.overviewSpeech,
      `MONUMENT OVERVIEW • ${currentStop.era}`
    );
    speakText(currentStop.overviewSpeech);
  }, [currentStop, setGpsPosition, appendMessage, speakText]);

  const askHistoricalRag = useCallback(() => {
    setTourPhase('HISTORICAL_RAG');
    setRagTelemetry(buildRagTelemetry(currentStop, 'HISTORICAL'));

    appendMessage(
      'USER',
      '🎙️ "Tell me more historical and cultural details about this monument."',
      'RAG QUERY: CLASSICAL HISTORY'
    );
    appendMessage(
      'AURELIUS',
      currentStop.historicalRag.answerSpeech,
      `QDRANT VECTOR RAG • ${currentStop.historicalRag.latencyMs}ms`
    );
    speakText(currentStop.historicalRag.answerSpeech);
  }, [currentStop, appendMessage, speakText]);

  const askGastroRag = useCallback(() => {
    setTourPhase('GASTRO_RAG');
    setRagTelemetry(buildRagTelemetry(currentStop, 'GASTRO'));

    appendMessage(
      'USER',
      '🎙️ "Where can I get a great coffee or traditional Roman food nearby?"',
      'RAG QUERY: GEO-GASTRONOMY'
    );
    appendMessage(
      'AURELIUS',
      currentStop.gastroRag.answerSpeech,
      `GEO-RAG PLACES • ${currentStop.gastroRag.latencyMs}ms`
    );
    speakText(currentStop.gastroRag.answerSpeech);
  }, [currentStop, appendMessage, speakText]);

  const advanceToNextStop = useCallback(() => {
    const nextIdx = currentStopIndex + 1;
    if (nextIdx < ROME_STOPS.length) {
      walkToStopIndex(nextIdx);
    } else {
      setTourPhase('TOUR_COMPLETED');
      const farewell =
        'Optime! You have completed all five stops across Republican and Imperial Rome—from the Curia of Pompey to Hadrian’s Pantheon. May Fortuna guide your steps!';
      appendMessage('AURELIUS', farewell, 'TOUR COMPLETED');
      speakText(farewell);
    }
  }, [currentStopIndex, walkToStopIndex, appendMessage, speakText]);

  const finishTour = useCallback(() => {
    setTourPhase('TOUR_COMPLETED');
    const summaryText = `We have concluded our walk at ${currentStop.name}. Whenever you are ready, you can select any monument on the map to resume exploring Ancient Rome.`;
    appendMessage('USER', '🎙️ "Let’s finish the tour here for today."', 'VOICE INTENT');
    appendMessage('AURELIUS', summaryText, 'SESSION ENDED');
    speakText(summaryText);
  }, [currentStop, appendMessage, speakText]);

  const resetTour = useCallback(() => {
    stopSpeech();
    setCurrentStopIndex(0);
    setGpsPosition(ROME_STOPS[0].coords);
    setTourPhase('READY_TO_ARRIVE');
    setRagTelemetry(buildRagTelemetry(ROME_STOPS[0], 'OVERVIEW'));
    setMessages([
      {
        id: `reset_${Date.now()}`,
        sender: 'AURELIUS',
        tag: 'PERIPATETIC GPS GUIDE',
        timestamp: '09:30 AM',
        text: `Tour reset to Stop #1: ${ROME_STOPS[0].name}. Tap "Simulate 'I Have Arrived'" to begin the voice overview.`
      }
    ]);
  }, [stopSpeech, setGpsPosition]);

  return (
    <TourContext.Provider
      value={{
        stops: ROME_STOPS,
        activePage,
        setActivePage,
        layoutMode,
        setLayoutMode,
        currentStopIndex,
        currentStop,
        tourPhase,
        messages,
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
