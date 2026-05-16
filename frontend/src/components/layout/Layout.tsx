import type { ReactNode } from 'react';
import { Sidebar } from './Sidebar';
import { TopBar } from './TopBar';

interface LayoutProps {
  children: ReactNode;
}

export const Layout: React.FC<LayoutProps> = ({ children }) => {
  return (
    <div className="layout-container">
      <Sidebar />
      <div className="main-content">
        <TopBar />
        <div className="content-area">
          {children}
        </div>
      </div>
    </div>
  );
};
