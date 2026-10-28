import { useEffect, useState } from 'react';
import { TourProvider } from './store/TourContext';
import { MainLayout } from './layouts/MainLayout/MainLayout';
import { AppRouter } from './router/AppRouter';
import { checkBackendHealth } from './lib/api';
import { saveTheme } from './lib/theme';
import './App.css';

export function App() {
  const [theme, setTheme] = useState(() => document.documentElement.dataset.theme);

  function toggleTheme() {
    const nextTheme = theme === 'dark' ? 'light' : 'dark';
    document.documentElement.dataset.theme = nextTheme;
    setTheme(nextTheme);
    saveTheme(nextTheme, {
      setItem: (key, value) => window.localStorage.setItem(key, value)
    });
  }

  useEffect(() => {
    const controller = new AbortController();

    checkBackendHealth(controller.signal).catch((error) => {
      if (controller.signal.aborted) return;
      console.error('Backend health check failed:', error);
    });

    return () => controller.abort();
  }, []);

  return (
    <TourProvider>
      <div className="app-shell">
        <MainLayout theme={theme} onToggleTheme={toggleTheme}>
          <AppRouter />
        </MainLayout>
      </div>
    </TourProvider>
  );
}

export default App;
