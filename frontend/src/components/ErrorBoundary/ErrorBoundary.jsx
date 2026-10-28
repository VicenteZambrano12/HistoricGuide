import { Component } from 'react';
import { createCorrelationId, getErrorContext, logger } from '../../lib/logger.js';
import { getSavedLanguage, getTranslator } from '../../i18n/translations.js';
import './ErrorBoundary.css';

export class ErrorBoundary extends Component {
  state = { hasError: false, reference: null };

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error, info) {
    const reference = getErrorContext(error).correlationId ?? createCorrelationId();
    logger.error('react.render_failed', {
      error,
      reference,
      componentStack: info.componentStack
    });
    this.setState({ reference });
  }

  render() {
    if (!this.state.hasError) return this.props.children;
    const t = getTranslator(getSavedLanguage({
      getItem: (key) => window.localStorage.getItem(key)
    }));
    return (
      <main className="error-boundary">
        <section className="error-boundary__panel" role="alert" aria-labelledby="crash-title">
          <span className="error-boundary__brand">Plinius</span>
          <h1 id="crash-title">{t('crashTitle')}</h1>
          <p>{t('crashDescription')}</p>
          <div className="error-boundary__actions">
            <button type="button" onClick={() => {
              logger.info('react.render_retry', { reference: this.state.reference });
              this.setState({ hasError: false, reference: null });
            }}>{t('crashRetry')}</button>
            <button type="button" onClick={() => window.location.reload()}>{t('crashReload')}</button>
          </div>
          {this.state.reference && (
            <p className="error-boundary__reference">
              {t('errorReference', { reference: this.state.reference })}
            </p>
          )}
        </section>
      </main>
    );
  }
}
