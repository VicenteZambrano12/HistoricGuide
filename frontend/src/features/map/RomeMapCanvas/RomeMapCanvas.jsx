import React from 'react';
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
    walkProgress,
    walkToStopIndex,
    confirmArrivalAtStop
  } = useTour();

  const routePoints = stops.map((s) => `${s.coords.mapX},${s.coords.mapY}`).join(' ');

  return (
    <section className="rome-map">
      <div className="rome-map__header">
        <span className="rome-map__title">
          🗺️ FORMA URBIS ROMAE // INTERACTIVE PERIPATETIC RADAR
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
                stroke="rgba(212, 175, 55, 0.06)"
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
            fill="rgba(212, 175, 55, 0.03)"
            stroke="rgba(212, 175, 55, 0.12)"
            strokeDasharray="4 4"
          />
          <text x="485" y="435" fill="rgba(212,175,55,0.28)" fontSize="11" fontFamily="Cinzel">
            MONS PALATINUS
          </text>

          <ellipse
            cx="575"
            cy="220"
            rx="90"
            ry="52"
            fill="rgba(212, 175, 55, 0.03)"
            stroke="rgba(212, 175, 55, 0.12)"
            strokeDasharray="4 4"
          />
          <text x="535" y="220" fill="rgba(212,175,55,0.28)" fontSize="11" fontFamily="Cinzel">
            COLLIS QUIRINALIS
          </text>

          <text x="190" y="145" fill="rgba(212,175,55,0.28)" fontSize="12" fontFamily="Cinzel">
            CAMPUS MARTIUS
          </text>

          {/* Tiber River (Flumen Tiberis) */}
          <path
            d="M 140,0 C 125,120 110,220 185,310 C 255,390 215,470 165,540"
            fill="none"
            stroke="rgba(56, 189, 248, 0.18)"
            strokeWidth="36"
            strokeLinecap="round"
          />
          <path
            d="M 140,0 C 125,120 110,220 185,310 C 255,390 215,470 165,540"
            fill="none"
            stroke="rgba(56, 189, 248, 0.45)"
            strokeWidth="2"
            strokeDasharray="6 6"
          />
          <text x="72" y="275" fill="rgba(56, 189, 248, 0.5)" fontSize="10" fontFamily="Cinzel">
            FLUMEN TIBERIS
          </text>

          {/* Tour Walking Route */}
          <polyline
            points={routePoints}
            fill="none"
            stroke="rgba(212, 175, 55, 0.45)"
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
                    fill="rgba(212, 175, 55, 0.16)"
                    stroke="#d4af37"
                    strokeWidth="1.5"
                    strokeDasharray="3 3"
                  />
                )}
                <circle
                  r="14"
                  fill={isSelected ? '#d4af37' : isVisited ? '#2b251c' : '#171411'}
                  stroke="#d4af37"
                  strokeWidth="2"
                />
                <text
                  textAnchor="middle"
                  dy="4"
                  fill={isSelected ? '#0b0a09' : '#f5f2eb'}
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
                  fill="rgba(14, 12, 10, 0.9)"
                  stroke={isSelected ? '#d4af37' : 'rgba(255,255,255,0.12)'}
                />
                <text
                  x="0"
                  y="35"
                  textAnchor="middle"
                  fill={isSelected ? '#d4af37' : '#c8c1b4'}
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
              <circle r="7" fill="#38bdf8" stroke="#0b0a09" strokeWidth="2" />
            </g>
          )}
        </svg>

        <div className="rome-map__floating-hud">
          <div className="rome-map__hud-info">
            <span className="rome-map__hud-label">
              {isWalking
                ? `WALKING ALONG VIA SACRA (${walkProgress}%)`
                : `CURRENT STOP #${currentStop.order} • ${currentStop.era}`}
            </span>
            <span className="rome-map__hud-stop">{currentStop.name}</span>
          </div>

          <button
            type="button"
            className="rome-map__arrive-btn"
            disabled={isWalking}
            onClick={confirmArrivalAtStop}
          >
            {tourPhase === 'READY_TO_ARRIVE'
              ? "📍 Simulate 'I Have Arrived'"
              : '🔄 Replay Arrival Overview'}
          </button>
        </div>
      </div>
    </section>
  );
}
