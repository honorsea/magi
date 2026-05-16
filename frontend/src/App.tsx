import { useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Layout } from './components/layout/Layout';
import { DashboardPage } from './pages/DashboardPage';
import { SimulationPage } from './pages/SimulationPage';
import { KpiPage } from './pages/KpiPage';
import { AgentPage } from './pages/AgentPage';
import { LeanPage } from './pages/LeanPage';
import { OutputsPage } from './pages/OutputsPage';
import { SettingsPage } from './pages/SettingsPage';

function App() {
  // Theme initialization
  useEffect(() => {
    const savedTheme = localStorage.getItem('magi-theme') || 'light';
    document.documentElement.setAttribute('data-theme', savedTheme);
  }, []);

  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/sim/:id" element={<SimulationPage />} />
          <Route path="/kpis" element={<KpiPage />} />
          <Route path="/agent" element={<AgentPage />} />
          <Route path="/lean" element={<LeanPage />} />
          <Route path="/outputs" element={<OutputsPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}

export default App;
