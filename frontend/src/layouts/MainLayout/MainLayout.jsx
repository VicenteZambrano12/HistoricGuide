import { Navbar } from '../../components/Navbar/Navbar';
import './MainLayout.css';

export function MainLayout({ children, theme, onToggleTheme }) {
  return (
    <div className="main-layout">
      <Navbar theme={theme} onToggleTheme={onToggleTheme} />
      <main className="main-layout__content">{children}</main>
    </div>
  );
}
