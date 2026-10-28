import { useTour } from '../../../store/TourContext';
import './StopTimelineBar.css';

export function StopTimelineBar() {
  const { stops, currentStopIndex, walkToStopIndex, t } = useTour();
  const routeRef = useRef(null);

  useEffect(() => {
    const route = routeRef.current;
    const currentItem = route.querySelector('[aria-current="step"]');
    route.scrollTo({
      left: currentItem.offsetLeft,
      behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth'
    });
  }, [currentStopIndex]);

  return (
    <nav className="stop-timeline" ref={routeRef} aria-label={t('tourRoute')}>
      {stops.map((stop, idx) => {
        const isActive = idx === currentStopIndex;
        return (
          <button
            key={stop.id}
            type="button"
            className={`stop-timeline__item ${isActive ? 'stop-timeline__item--active' : ''}`}
            onClick={() => walkToStopIndex(idx)}
            aria-current={isActive ? 'step' : undefined}
          >
            <div className="stop-timeline__top">
              <span className="stop-timeline__number">{stop.order}</span>
              <span>{t(isActive ? 'selectedStop' : 'stop')} {isActive ? '' : stop.order}</span>
            </div>
            <div className="stop-timeline__name">{stop.name}</div>
            <div className="stop-timeline__era">{stop.era}</div>
          </button>
        );
      })}
    </nav>
  );
}
import { useEffect, useRef } from 'react';
