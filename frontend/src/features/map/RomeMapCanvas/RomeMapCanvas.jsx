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
    isVoiceRecording,
    walkProgress,
    walkToStopIndex,
    confirmArrivalAtStop,
    t
  } = useTour();

  const routePoints = stops.map((s) => `${s.coords.mapX},${s.coords.mapY}`).join(' ');

  return (
    <section className="rome-map">
      <div className="rome-map__header">
        <span className="rome-map__title">
          {t('mapTitle')}
        </span>
        <span className="rome-map__gps-pill">
          GPS: {formatCoordinates(gpsPosition?.lat, gpsPosition?.lng)}
        </span>
      </div>

      <div className="rome-map__stage">
        <svg className="rome-map__svg" viewBox="0 0 700 540">
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
          <text x="485" y="435" fill="var(--map-terrain-label)" fontSize="11" fontFamily="Cinzel">
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
          <text x="535" y="220" fill="var(--map-terrain-label)" fontSize="11" fontFamily="Cinzel">
            COLLIS QUIRINALIS
          </text>

          <text x="190" y="145" fill="var(--map-terrain-label)" fontSize="12" fontFamily="Cinzel">
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
          <text x="72" y="275" fill="var(--map-river-label)" fontSize="10" fontFamily="Cinzel">
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
              >
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
                  dy="4"
                  fill={isSelected ? 'var(--on-gold)' : 'var(--text-marble)'}
                  fontSize="11"
                  fontWeight="700"
                  fontFamily="JetBrains Mono"
                >
                  {stop.order}
                </text>
                <rect
                  x="-78"
                  y="20"
                  width="156"
                  height="22"
                  rx="5"
                  fill="var(--map-label)"
                  stroke={isSelected ? 'var(--gold-primary)' : 'var(--border-subtle)'}
                />
                <text
                  x="0"
                  y="35"
                  textAnchor="middle"
                  fill={isSelected ? 'var(--gold-primary)' : 'var(--text-travertine)'}
                  fontSize="10"
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
              <circle r="18" fill="rgba(56, 189, 248, 0.22)" />
              <circle r="7" fill="var(--cyan-gps)" stroke="var(--bg-obsidian)" strokeWidth="2" />
            </g>
          )}
        </svg>

        <div className="rome-map__floating-hud">
          <div className="rome-map__hud-info">
            <span className="rome-map__hud-label">
              {isWalking
                ? t('walking', { progress: walkProgress })
                : t('currentStop', { order: currentStop.order, era: currentStop.era })}
            </span>
            <span className="rome-map__hud-stop">{currentStop.name}</span>
          </div>

          <button
            type="button"
            className="rome-map__arrive-btn"
            disabled={isWalking || isChatPending || isVoiceRecording}
            onClick={confirmArrivalAtStop}
          >
            {t(tourPhase === 'READY_TO_ARRIVE' ? 'arrivalButton' : 'replayArrival')}
          </button>
        </div>
      </div>
    </section>
  );
}
