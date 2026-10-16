import React from 'react';
import { TourProvider } from './store/TourContext';
import { MainLayout } from './layouts/MainLayout/MainLayout';
import { AppRouter } from './router/AppRouter';
import './App.css';

export function App() {
  return (
    <TourProvider>
      <div className="app-shell">
        <MainLayout>
          <AppRouter />
        </MainLayout>
      </div>
    </TourProvider>
  );
}

export default App;
