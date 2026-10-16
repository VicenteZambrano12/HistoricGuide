import React from 'react';
import { useTour } from '../../../store/TourContext';
import './StopTimelineBar.css';

export function StopTimelineBar() {
  const { stops, currentStopIndex, walkToStopIndex } = useTour();

  return (
    <div className="stop-timeline">
      {stops.map((stop, idx) => {
        const isActive = idx === currentStopIndex;
        return (
          <button
            key={stop.id}
            type="button"
            className={`stop-timeline__item ${isActive ? 'stop-timeline__item--active' : ''}`}
            onClick={() => walkToStopIndex(idx)}
          >
            <div className="stop-timeline__top">
              <span>STOP 0{stop.order}</span>
              <span>{stop.periodTag}</span>
            </div>
            <div className="stop-timeline__name">{stop.name}</div>
            <div className="stop-timeline__era">{stop.era}</div>
          </button>
        );
      })}
    </div>
  );
}
