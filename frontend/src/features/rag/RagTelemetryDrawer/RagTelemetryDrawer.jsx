import { useTour } from '../../../store/TourContext';
import { pdfSourceHref } from '../../../lib/pdfSources';
import './RagTelemetryDrawer.css';

export function RagTelemetryDrawer() {
  const { t, chatSources, isChatPending, isInteractionBusy } = useTour();
  return (
    <section className="rag-drawer" aria-label={t('sources')}>
      <h2 className="rag-drawer__title">{t('sources')}</h2>
      <div className="rag-drawer__panel" aria-live="polite">
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
                  aria-disabled={isInteractionBusy}
                  tabIndex={isInteractionBusy ? -1 : 0}
                  onClick={(event) => {
                    if (isInteractionBusy) event.preventDefault();
                  }}
                >
                  <span className="rag-drawer__filename">{source.source.split('/').at(-1)}</span>
                  <span className="rag-drawer__page">{t('sourcePage', { page: source.page })} &#8599;</span>
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
