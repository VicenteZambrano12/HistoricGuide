import './MonumentIllustration.css';
import { useTour } from '../../store/TourContext';

export function MonumentIllustration({ stop }) {
  const { t, stops } = useTour();
  if (!stop) return null;

  const renderArchitecturalVector = (id) => {
    switch (id) {
      case 'torre-argentina':
        return (
          <g stroke="var(--gold-primary)" strokeWidth="1.6" fill="none">
            <rect x="40" y="95" width="320" height="16" fill="rgba(212,175,55,0.12)" />
            {[70, 115, 160, 205, 250, 295].map((x, i) => (
              <g key={i}>
                <rect
                  x={x}
                  y={i % 2 === 0 ? 38 : 52}
                  width="14"
                  height={i % 2 === 0 ? 57 : 43}
                  fill="rgba(212,175,55,0.15)"
                />
                <line x1={x - 3} y1={i % 2 === 0 ? 38 : 52} x2={x + 17} y2={i % 2 === 0 ? 38 : 52} />
              </g>
            ))}
            <circle cx="330" cy="34" r="14" stroke="rgba(158,42,43,0.8)" fill="rgba(158,42,43,0.25)" />
          </g>
        );
      case 'forum-boarium':
        return (
          <g stroke="var(--gold-primary)" strokeWidth="1.6" fill="none">
            <polygon points="55,45 115,18 175,45" fill="rgba(212,175,55,0.16)" />
            {[68, 95, 122, 149].map((x) => (
              <rect key={x} x={x} y="45" width="10" height="52" fill="rgba(212,175,55,0.1)" />
            ))}
            <path d="M225,45 Q285,12 345,45 Z" fill="rgba(212,175,55,0.18)" />
            {[238, 262, 286, 310, 332].map((x) => (
              <line key={x} x1={x} y1="45" x2={x} y2="97" strokeWidth="4" />
            ))}
            <rect x="40" y="97" width="320" height="12" fill="rgba(212,175,55,0.14)" />
          </g>
        );
      case 'roman-forum':
        return (
          <g stroke="var(--gold-primary)" strokeWidth="1.6" fill="none">
            <polygon points="130,38 200,12 270,38" fill="rgba(212,175,55,0.16)" />
            <rect x="142" y="38" width="116" height="60" fill="rgba(212,175,55,0.08)" />
            <rect x="184" y="62" width="32" height="36" fill="rgba(212,175,55,0.22)" />
            {[55, 82, 108, 295, 325].map((x) => (
              <rect key={x} x={x} y="30" width="11" height="68" fill="rgba(212,175,55,0.14)" />
            ))}
            <rect x="35" y="98" width="330" height="12" fill="rgba(212,175,55,0.15)" />
          </g>
        );
      case 'trajans-markets':
        return (
          <g stroke="var(--gold-primary)" strokeWidth="1.6" fill="none">
            <path d="M55,102 A145,75 0 0,1 345,102" fill="rgba(158,42,43,0.15)" />
            {[85, 125, 165, 205, 245, 285, 315].map((x) => (
              <path
                key={x}
                d={`M${x - 10},98 L${x - 10},68 A10,10 0 0,1 ${x + 10},68 L${x + 10},98`}
                fill="rgba(212,175,55,0.14)"
              />
            ))}
            <rect x="192" y="14" width="16" height="86" fill="rgba(212,175,55,0.24)" />
          </g>
        );
      case 'pantheon':
      default:
        return (
          <g stroke="var(--gold-primary)" strokeWidth="1.6" fill="none">
            <path d="M75,78 A125,62 0 0,1 325,78 Z" fill="rgba(212,175,55,0.12)" />
            <polygon points="120,52 200,22 280,52" fill="rgba(212,175,55,0.2)" />
            {[132, 156, 180, 204, 228, 252, 268].map((x) => (
              <rect key={x} x={x} y="52" width="7" height="46" fill="rgba(212,175,55,0.15)" />
            ))}
            <rect x="65" y="98" width="270" height="10" fill="rgba(212,175,55,0.18)" />
          </g>
        );
    }
  };

  return (
    <header className="monument-art">
      <div className="monument-art__copy">
        <span className="monument-art__era">
          {t('tourPosition', { order: stop.order, total: stops.length })}
        </span>
        <h1 className="monument-art__name">{stop.name}</h1>
        <p className="monument-art__sub">{stop.subtitle}</p>
        <p className="monument-art__date">{stop.era}</p>
      </div>
      <svg className="monument-art__svg" viewBox="0 0 400 130" aria-hidden="true">
        {renderArchitecturalVector(stop.id)}
      </svg>
    </header>
  );
}
