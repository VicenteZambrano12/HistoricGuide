import React from 'react';
import { useTour } from '../store/TourContext';
import { TourWorkstationPage } from '../pages/TourWorkstationPage/TourWorkstationPage';
import { ArchitecturePreviewPage } from '../pages/ArchitecturePreviewPage/ArchitecturePreviewPage';
import './AppRouter.css';

export function AppRouter() {
  const { activePage } = useTour();

  return (
    <div className="app-router">
      {activePage === 'ARCHITECTURE' ? (
        <ArchitecturePreviewPage />
      ) : (
        <TourWorkstationPage />
      )}
    </div>
  );
}
