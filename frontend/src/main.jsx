import React from 'react';
import ReactDOM from 'react-dom/client';
import './theme.css';
import './index.css';
import App from './App.jsx';
import { getSavedTheme } from './lib/theme';

const storage = {
  getItem: (key) => window.localStorage.getItem(key)
};
document.documentElement.dataset.theme = getSavedTheme(storage);

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
