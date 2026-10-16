import React from 'react';
import { useTour } from '../../../store/TourContext';
import './ActionPromptChips.css';

export function ActionPromptChips() {
  const {
    tourPhase,
    isWalking,
    currentStopIndex,
    stops,
    confirmArrivalAtStop,
    askHistoricalRag,
    askGastroRag,
    advanceToNextStop,
    finishTour
  } = useTour();

  const hasNextStop = currentStopIndex < stops.length - 1;

  return (
    <div className="action-chips">
      <span className="action-chips__label">
        🎙️ SIMULATE VOICE TOURIST RESPONSES (POST-ARRIVAL OPTIONS)
      </span>

      <div className="action-chips__grid">
        {tourPhase === 'READY_TO_ARRIVE' || tourPhase === 'WALKING_TO_STOP' ? (
          <button
            type="button"
            className="action-chips__btn action-chips__btn--primary"
            disabled={isWalking}
            onClick={confirmArrivalAtStop}
          >
            📍 &ldquo;I&apos;ve arrived at the monument&rdquo; (Trigger Overview)
          </button>
        ) : (
          <>
            <button
              type="button"
              className="action-chips__btn action-chips__btn--rag"
              onClick={askHistoricalRag}
            >
              🏛️ 1. Historical &amp; Cultural Details (RAG)
            </button>

            <button
              type="button"
              className="action-chips__btn action-chips__btn--gastro"
              onClick={askGastroRag}
            >
              ☕ 2. Go to Coffee / Trattoria (Geo-RAG)
            </button>

            <button
              type="button"
              className="action-chips__btn"
              onClick={advanceToNextStop}
            >
              🚶 3. {hasNextStop ? 'Walk to Next Stop' : 'Complete Final Stop'}
            </button>

            <button
              type="button"
              className="action-chips__btn"
              onClick={finishTour}
            >
              🏁 4. Finish Tour Here
            </button>
          </>
        )}
      </div>
    </div>
  );
}
