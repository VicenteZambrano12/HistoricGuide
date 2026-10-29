import { useTour } from '../../../store/TourContext';
import { formatCoordinates } from '../../../utils/formatters';
import './RomeMapCanvas.css';

export function RomeMapCanvas() {
  const {
    stops,
    currentStopIndex,
    currentStop,
    tourPhase,
    gpsPosition,
    isWalking,
    isChatPending,
    isDemoReady,
    isVoiceRecording,
    walkProgress,
    walkToStopIndex,
    confirmArrivalAtStop,
    t
  } = useTour();

  const routePoints = stops.map((s) => `${s.coords.mapX},${s.coords.mapY}`).join(' ');

  return (
    <section className="rome-map" aria-labelledby="map-title">
      <div className="rome-map__header">
        <h2 id="map-title" className="rome-map__title">
          {t('mapTitle')}
        </h2>
        <span className="rome-map__gps-pill" title={`GPS: ${formatCoordinates(gpsPosition?.lat, gpsPosition?.lng)}`}>
          {t('simulatedRoute')}
        </span>
      </div>

      <div className="rome-map__stage">
        <svg className="rome-map__svg" viewBox="0 0 700 540" role="group" aria-label={t('tourRoute')}>
          <defs>
            <pattern id="romanGrid" width="40" height="40" patternUnits="userSpaceOnUse">
              <path
                d="M 40 0 L 0 0 0 40"
                fill="none"
                stroke="var(--map-grid)"
                strokeWidth="1"
              />
            </pattern>
          </defs>

          <rect width="700" height="540" fill="url(#romanGrid)" />
          <g fill="none" stroke="var(--map-contour)" strokeWidth="1.5" aria-hidden="true">
            <path d="M225 0L260 175 420 300 700 335M180 190L340 200 545 70M245 540L390 350 700 260M180 390L360 405 650 500M360 0L385 135 625 400M200 65L300 90 590 540" />
            <path d="M290 145L345 120 380 175 325 195ZM400 230L455 205 490 260 445 280ZM435 380L480 360 515 405 470 430ZM510 110L565 90 590 135 540 155Z" fill="var(--map-terrain)" />
          </g>

          {/* Ancient Aurelian Walls & Hills Contours */}
          <ellipse
            cx="520"
            cy="430"
            rx="95"
            ry="60"
            fill="var(--map-terrain)"
            stroke="var(--map-contour)"
            strokeDasharray="4 4"
          />
          <text x="485" y="435" fill="var(--map-terrain-label)" fontSize="11" fontFamily="var(--font-display)">
            MONS PALATINUS
          </text>

          <ellipse
            cx="575"
            cy="220"
            rx="90"
            ry="52"
            fill="var(--map-terrain)"
            stroke="var(--map-contour)"
            strokeDasharray="4 4"
          />
          <text x="535" y="220" fill="var(--map-terrain-label)" fontSize="11" fontFamily="var(--font-display)">
            COLLIS QUIRINALIS
          </text>

          <text x="190" y="145" fill="var(--map-terrain-label)" fontSize="12" fontFamily="var(--font-display)">
            CAMPUS MARTIUS
          </text>

          {/* Tiber River (Flumen Tiberis) */}
          <path
            d="M 140,0 C 125,120 110,220 185,310 C 255,390 215,470 165,540"
            fill="none"
            stroke="var(--map-river)"
            strokeWidth="36"
            strokeLinecap="round"
          />
          <path
            d="M 140,0 C 125,120 110,220 185,310 C 255,390 215,470 165,540"
            fill="none"
            stroke="var(--map-river-line)"
            strokeWidth="2"
            strokeDasharray="6 6"
          />
          <text x="72" y="275" fill="var(--map-river-label)" fontSize="10" fontFamily="var(--font-display)">
            FLUMEN TIBERIS
          </text>

          {/* Tour Walking Route */}
          <polyline
            points={routePoints}
            fill="none"
            stroke="var(--map-route)"
            strokeWidth="3"
            strokeDasharray="7 5"
          />

          {/* 5 Monument Pins */}
          {stops.map((stop, index) => {
            const isSelected = index === currentStopIndex;
            const isVisited = index < currentStopIndex;
            return (
              <g
                key={stop.id}
                className="rome-map__pin"
                transform={`translate(${stop.coords.mapX}, ${stop.coords.mapY})`}
                onClick={() => walkToStopIndex(index)}
                role="button"
                tabIndex={0}
                aria-label={t('mapStop', { order: stop.order, name: stop.name })}
                aria-current={isSelected ? 'location' : undefined}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' || event.key === ' ') {
                    event.preventDefault();
                    walkToStopIndex(index);
                  }
                }}
              >
                <circle r="30" fill="transparent" />
                {isSelected && (
                  <circle
                    r="24"
                    fill="var(--gold-soft)"
                    stroke="var(--gold-primary)"
                    strokeWidth="1.5"
                    strokeDasharray="3 3"
                  />
                )}
                <circle
                  r="14"
                  fill={isSelected ? 'var(--gold-primary)' : isVisited ? 'var(--map-pin-visited)' : 'var(--map-pin)'}
                  stroke="var(--gold-primary)"
                  strokeWidth="2"
                />
                <text
                  textAnchor="middle"
                  dy="0.35em"
                  fill={isSelected ? 'var(--on-gold)' : 'var(--text-marble)'}
                  fontSize="11"
                  fontWeight="700"
                  fontFamily="var(--font-sans)"
                >
                  {stop.order}
                </text>
                <rect
                  x="-94"
                  y="20"
                  width="188"
                  height="26"
                  rx="5"
                  fill="var(--map-label)"
                  stroke={isSelected ? 'var(--gold-primary)' : 'var(--border-subtle)'}
                />
                <text
                  x="0"
                  y="37"
                  textAnchor="middle"
                  fill={isSelected ? 'var(--gold-primary)' : 'var(--text-travertine)'}
                  fontSize="12"
                  fontWeight="600"
                >
                  {stop.name}
                </text>
              </g>
            );
          })}

          {/* Animated Live User GPS Marker */}
          {gpsPosition && (
            <g transform={`translate(${gpsPosition.mapX}, ${gpsPosition.mapY})`}>
              <circle className="rome-map__gps-ring" r="18" fill="none" stroke="var(--cyan-gps)" strokeWidth="2" />
            </g>
          )}
        </svg>
        <div className="rome-map__legend" aria-hidden="true">
          <span><i className="rome-map__route-key" />{t('tourRoute')}</span>
          <span><i className="rome-map__position-key" />{t('yourPosition')}</span>
        </div>

        <div className="rome-map__floating-hud">
          <div className="rome-map__hud-info">
            <span className="rome-map__hud-label" role="status">
              {isWalking
                ? t('walking', { progress: walkProgress })
                : t('currentStop', { order: currentStop.order, era: currentStop.era })}
            </span>
            <span className="rome-map__hud-stop">{currentStop.name}</span>
          </div>

          <button
            type="button"
            className="rome-map__arrive-btn"
            disabled={isWalking || isChatPending || isVoiceRecording || !isDemoReady}
            onClick={confirmArrivalAtStop}
          >
            {t(tourPhase === 'READY_TO_ARRIVE' ? 'arrivalButton' : 'replayArrival')}
          </button>
        </div>
      </div>
    </section>
  );
}
