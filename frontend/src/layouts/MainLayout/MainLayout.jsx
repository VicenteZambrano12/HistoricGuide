import React from 'react';
import { Navbar } from '../../components/Navbar/Navbar';
import './MainLayout.css';

export function MainLayout({ children }) {
  return (
    <div className="main-layout">
      <Navbar />
      <main className="main-layout__content">{children}</main>
    </div>
  );
}
