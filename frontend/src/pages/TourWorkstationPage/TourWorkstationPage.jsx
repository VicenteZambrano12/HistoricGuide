import React from 'react';
import { useTour } from '../../store/TourContext';
import { StopTimelineBar } from '../../features/map/StopTimelineBar/StopTimelineBar';
import { RomeMapCanvas } from '../../features/map/RomeMapCanvas/RomeMapCanvas';
import { HistorianVoicePanel } from '../../features/voiceGuide/HistorianVoicePanel/HistorianVoicePanel';
import { RagTelemetryDrawer } from '../../features/rag/RagTelemetryDrawer/RagTelemetryDrawer';
import { MonumentIllustration } from '../../components/MonumentIllustration/MonumentIllustration';
import './TourWorkstationPage.css';

export function TourWorkstationPage() {
  const { layoutMode, currentStop } = useTour();

  return (
    <div
      className={`workstation-page ${
        layoutMode === 'MOBILE' ? 'workstation-page--mobile' : ''
      }`}
    >
      <MonumentIllustration stop={currentStop} />
      <StopTimelineBar />

      <div className="workstation-page__grid">
        <div className="workstation-page__left">
          <RomeMapCanvas />
          <RagTelemetryDrawer />
        </div>

        <HistorianVoicePanel />
      </div>
    </div>
  );
}
