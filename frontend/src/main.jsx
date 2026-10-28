import React from 'react';
import ReactDOM from 'react-dom/client';
import './theme.css';
import './index.css';
import App from './App.jsx';
import { getSavedTheme } from './lib/theme';
import { ErrorBoundary } from './components/ErrorBoundary/ErrorBoundary';
import { installGlobalErrorHandlers } from './lib/globalErrors.js';

const removeGlobalHandlers = installGlobalErrorHandlers();
if (import.meta.hot) import.meta.hot.dispose(removeGlobalHandlers);

const storage = {
  getItem: (key) => window.localStorage.getItem(key)
};
document.documentElement.dataset.theme = getSavedTheme(storage);

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </React.StrictMode>
);
