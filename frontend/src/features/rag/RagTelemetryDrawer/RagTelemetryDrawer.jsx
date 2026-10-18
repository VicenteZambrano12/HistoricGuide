import { useTour } from '../../../store/TourContext';
import { pdfSourceHref } from '../../../lib/pdfSources';
import './RagTelemetryDrawer.css';

export function RagTelemetryDrawer() {
  const { t, chatSources, isChatPending } = useTour();
  return (
    <section className="rag-drawer" aria-label={t('sources')}>
      <div className="rag-drawer__tabs" role="tablist" aria-label={t('sources')}>
        <button
          className="rag-drawer__tab"
          type="button"
          role="tab"
          id="sources-tab"
          aria-selected="true"
          aria-controls="sources-panel"
        >
          {t('sources')}
        </button>
      </div>
      <div
        className="rag-drawer__panel"
        role="tabpanel"
        id="sources-panel"
        aria-labelledby="sources-tab"
        tabIndex={0}
      >
        {chatSources.length ? (
          <ul className="rag-drawer__sources">
            {chatSources.map((source) => (
              <li key={`${source.source}:${source.page}`}>
                <a
                  className="rag-drawer__source"
                  href={pdfSourceHref(source)}
                  target="_blank"
                  rel="noopener noreferrer"
                  title={t('openSourcePdf', { page: source.page })}
                >
                  <span className="rag-drawer__filename">{source.source.split('/').at(-1)}</span>
                  <span className="rag-drawer__page">{t('sourcePage', { page: source.page })} &nearr;</span>
                </a>
              </li>
            ))}
          </ul>
        ) : (
          <p className="rag-drawer__empty">
            {t(isChatPending ? 'sourcesLoading' : 'sourcesEmpty')}
          </p>
        )}
      </div>
    </section>
  );
}
