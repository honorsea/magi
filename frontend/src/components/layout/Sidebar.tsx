import { useEffect, useState } from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutDashboard, BarChart2, MessageSquare, Network, Settings, FolderOpen } from 'lucide-react';

const NAV_ITEMS = [
  { path: '/', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/kpis', label: 'KPIs & Metrics', icon: BarChart2 },
  { path: '/agent', label: 'Cognitive Agent', icon: MessageSquare },
  { path: '/lean', label: 'Lean KG', icon: Network },
  { path: '/outputs', label: 'Outputs', icon: FolderOpen },
  { path: '/settings', label: 'Settings', icon: Settings },
];

export const Sidebar = () => {
  const [title, setTitle] = useState('MAGI');

  useEffect(() => {
    fetch('/api/branding')
      .then(res => res.json())
      .then(data => {
        if (data.title) setTitle(data.title);
        if (data.accent_color) {
          document.documentElement.style.setProperty('--accent-blue', data.accent_color);
        }
      })
      .catch(err => console.error('Failed to load branding', err));
  }, []);

  return (
    <div className="sidebar" style={{ display: 'flex', flexDirection: 'column' }}>
      <div style={{ height: '60px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', padding: '0 24px' }}>
        <h1 style={{ fontSize: '18px', fontWeight: 700, margin: 0 }}>{title}</h1>
      </div>
      
      <nav style={{ padding: '16px 8px', flex: 1 }}>
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) => 
                `nav-link ${isActive ? 'active' : ''}`
              }
              style={({ isActive }) => ({
                display: 'flex',
                alignItems: 'center',
                padding: '10px 16px',
                marginBottom: '4px',
                borderRadius: '6px',
                color: isActive ? 'var(--accent-blue)' : 'var(--text-secondary)',
                backgroundColor: isActive ? 'var(--bg-tertiary)' : 'transparent',
                fontWeight: isActive ? 600 : 500,
                transition: 'all 0.15s ease'
              })}
            >
              <Icon size={18} style={{ marginRight: '12px' }} />
              {item.label}
            </NavLink>
          );
        })}
      </nav>
      
      <div style={{ padding: '16px', borderTop: '1px solid var(--border)', fontSize: '12px', color: 'var(--text-secondary)' }}>
        Silverline Assembly Line Digital Twin
      </div>
    </div>
  );
};
