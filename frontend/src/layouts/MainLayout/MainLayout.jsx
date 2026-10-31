import { Navbar } from '../../components/Navbar/Navbar';
import { useTour } from '../../store/TourContext';
import './MainLayout.css';

export function MainLayout({ children, theme, onToggleTheme }) {
  const { t, isInteractionBusy } = useTour();
  return (
    <div className="main-layout">
      <a className="skip-link" href="#tour-content">{t('skipToTour')}</a>
      <Navbar theme={theme} onToggleTheme={onToggleTheme} />
      <main id="tour-content" className="main-layout__content" tabIndex={-1} aria-busy={isInteractionBusy}>{children}</main>
    </div>
  );
}
