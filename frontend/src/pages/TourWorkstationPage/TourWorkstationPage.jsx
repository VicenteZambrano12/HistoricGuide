import React from 'react';
import { useTour } from '../../store/TourContext';
import { StopTimelineBar } from '../../features/map/StopTimelineBar/StopTimelineBar';
import { RomeMapCanvas } from '../../features/map/RomeMapCanvas/RomeMapCanvas';
import { HistorianVoicePanel } from '../../features/voiceGuide/HistorianVoicePanel/HistorianVoicePanel';
import { RagTelemetryDrawer } from '../../features/rag/RagTelemetryDrawer/RagTelemetryDrawer';
import './TourWorkstationPage.css';

export function TourWorkstationPage() {
  const { layoutMode } = useTour();

  return (
    <div
      className={`workstation-page ${
        layoutMode === 'MOBILE' ? 'workstation-page--mobile' : ''
      }`}
    >
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
