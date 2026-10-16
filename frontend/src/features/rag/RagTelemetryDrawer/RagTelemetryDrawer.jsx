import React from 'react';
import { useTour } from '../../../store/TourContext';
import { formatConfidence } from '../../../utils/formatters';
import './RagTelemetryDrawer.css';

export function RagTelemetryDrawer() {
  const { ragTelemetry } = useTour();

  if (!ragTelemetry) return null;

  return (
    <section className="rag-drawer">
      <div className="rag-drawer__header">
        <span className="rag-drawer__badge">{ragTelemetry.badge}</span>
        <span className="rag-drawer__metrics">
          COLLECTION: {ragTelemetry.collection} • LATENCY: {ragTelemetry.latencyMs}ms
        </span>
      </div>

      <div className="rag-drawer__query">{ragTelemetry.query}</div>

      <div className="rag-drawer__chunks">
        {ragTelemetry.items.map((item) => (
          <article key={item.id} className="rag-drawer__chunk">
            <div className="rag-drawer__chunk-top">
              <span className="rag-drawer__chunk-title">{item.title}</span>
              <span className="rag-drawer__score">{formatConfidence(item.score)}</span>
            </div>
            <span className="rag-drawer__chunk-sub">{item.subtitle}</span>
            <p className="rag-drawer__chunk-snippet">{item.snippet}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
