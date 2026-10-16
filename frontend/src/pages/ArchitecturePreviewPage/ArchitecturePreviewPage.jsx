import React from 'react';
import { ROME_STOPS } from '../../lib/romeStopsData';
import { MonumentIllustration } from '../../components/MonumentIllustration/MonumentIllustration';
import './ArchitecturePreviewPage.css';

export function ArchitecturePreviewPage() {
  const uiStates = [
    {
      step: 'SCREEN STATE 01 // PERIPATETIC GPS MAP',
      title: 'Interactive Forma Urbis Radar',
      desc: 'Simulates walking between 5 Republican & Imperial monuments along the Tiber and Via Sacra with real-time coordinate interpolation.'
    },
    {
      step: 'SCREEN STATE 02 // GEOFENCE ARRIVAL OVERVIEW',
      title: 'Voice AI Monument Introduction',
      desc: 'When the user indicates arrival, Aurelius delivers a historically grounded overview of the monument and prompts for next actions.'
    },
    {
      step: 'SCREEN STATE 03 // CLASSICAL RAG DEEP DIVE',
      title: 'Primary Sources Vector Retrieval',
      desc: 'Queries embedded passages from Suetonius, Livy, Vitruvius, and Cassius Dio with live cosine similarity telemetry.'
    },
    {
      step: 'SCREEN STATE 04 // GASTRO GEO-RAG',
      title: 'Proximity Espresso & Trattoria RAG',
      desc: 'Performs geo-spatial filtering around the monument coordinates to recommend authentic Roman roasteries and historic osterie.'
    }
  ];

  return (
    <div className="arch-page">
      <div className="arch-page__hero">
        <h2 className="arch-page__title">
          AURELIUS // UI SCREENS &amp; MODULAR RAG ARCHITECTURE
        </h2>
        <p className="arch-page__subtitle">
          Built with strict modular separation: one JSX + one CSS file per component and feature,
          powered by a conversational state machine and dual-index RAG (Classical History Corpus +
          Geo-Spatial Roman Gastronomy).
        </p>
      </div>

      <div className="arch-page__screens">
        {uiStates.map((item) => (
          <div key={item.step} className="arch-page__card">
            <span className="arch-page__step">{item.step}</span>
            <h3 className="arch-page__card-title">{item.title}</h3>
            <p className="arch-page__card-desc">{item.desc}</p>
          </div>
        ))}
      </div>

      <h3 className="arch-page__title">5 Curated Ancient Rome Stops (Vector Artwork Previews)</h3>
      <div className="arch-page__stops-gallery">
        {ROME_STOPS.map((stop) => (
          <MonumentIllustration key={stop.id} stop={stop} />
        ))}
      </div>
    </div>
  );
}
