import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useSimStore } from '../store/simulationStore';
import { useKpiStore } from '../store/kpiStore';
import { AssemblyLineCanvas } from '../components/simulation/AssemblyLineCanvas';
import { SimControls } from '../components/simulation/SimControls';
import { ParamPanel } from '../components/simulation/ParamPanel';
import { ArrowLeft, Activity, AlertTriangle, Loader } from 'lucide-react';

export const SimulationPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { activeSession, setActiveSession, ws, fetchSessions } = useSimStore();
  const { updateKpis, reset } = useKpiStore();
  const [taskQueue, setTaskQueue] = useState<any[]>([]);

  // Load and subscribe when the sim ID changes
  useEffect(() => {
    if (!id) { navigate('/'); return; }
    reset();
    setTaskQueue([]);
    setActiveSession(id);

    // Poll session status every 2s so cards update
    const poll = setInterval(() => fetchSessions(), 2000);
    return () => {
      clearInterval(poll);
      // Do NOT call setActiveSession(null) — keeps the WS alive if user navigates back quickly
    };
  }, [id]);

  // Subscribe to WebSocket events
  useEffect(() => {
    if (!ws) return;
    const cleanup = ws.onMessage((msg: any) => {
      if (msg.type === 'kpi_snapshot') {
        updateKpis(msg.data, msg.data.sim_time_s ?? 0);
      } else if (msg.type === 'task_record') {
        setTaskQueue(prev => [...prev, msg.data].slice(-100));
      } else if (msg.type === 'sim_error') {
        // Status will be updated on next poll
        fetchSessions();
      } else if (msg.type === 'sim_complete') {
        fetchSessions();
      }
    });
    return () => { cleanup(); };
  }, [ws]);

  // Loading state
  if (!activeSession) {
    return (
      <div style={{ padding: '60px', textAlign: 'center', color: 'var(--text-secondary)' }}>
        <Loader size={32} style={{ opacity: 0.4, marginBottom: '12px', display: 'block', margin: '0 auto 12px' }} />
        <p>Loading simulation data…</p>
      </div>
    );
  }

  const isActive = activeSession.status === 'running' || activeSession.status === 'paused';
  const isError  = activeSession.status === 'error';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', gap: '16px' }}>
      {/* Header bar */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexShrink: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <button
            onClick={() => navigate('/')}
            style={{ background: 'var(--bg-tertiary)', border: 'none', padding: '8px', borderRadius: '6px',
              cursor: 'pointer', color: 'var(--text-primary)', display: 'flex', alignItems: 'center' }}
          >
            <ArrowLeft size={18} />
          </button>
          <div>
            <h2 style={{ margin: 0, fontSize: '18px' }}>{activeSession.label}</h2>
            <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
              ID: {activeSession.id} &nbsp;·&nbsp; Mode: {activeSession.mode.toUpperCase()}
            </span>
          </div>
          <span style={{
            padding: '3px 10px', borderRadius: '10px', fontSize: '12px', fontWeight: 600,
            backgroundColor: activeSession.status === 'running' ? 'var(--accent-green)' :
                             activeSession.status === 'paused'  ? 'var(--accent-amber)' :
                             activeSession.status === 'error'   ? 'var(--accent-red)'   :
                             'var(--bg-tertiary)',
            color: ['running','paused','error'].includes(activeSession.status) ? 'white' : 'var(--text-secondary)'
          }}>
            {activeSession.status.toUpperCase()}
          </span>
        </div>
        <SimControls session={activeSession} />
      </div>

      {/* Error banner */}
      {isError && activeSession.error_msg && (
        <div style={{
          padding: '12px 16px', borderRadius: '8px', background: 'var(--status-error-bg)',
          border: '1px solid var(--status-error-border)', color: 'var(--accent-red)',
          display: 'flex', alignItems: 'flex-start', gap: '10px', flexShrink: 0
        }}>
          <AlertTriangle size={18} style={{ flexShrink: 0, marginTop: '1px' }} />
          <div>
            <strong>Simulation Error</strong>
            <pre style={{ margin: '4px 0 0 0', fontSize: '12px', fontFamily: 'var(--font-mono)',
              whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
              {activeSession.error_msg}
            </pre>
          </div>
        </div>
      )}

      {/* Main content */}
      <div style={{ display: 'flex', gap: '16px', flex: 1, minHeight: 0 }}>
        {/* Left: canvas + event stream */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '16px', minWidth: 0 }}>
          <div className="card" style={{ flex: 3, position: 'relative', overflow: 'hidden', minHeight: '300px' }}>
            <AssemblyLineCanvas events={taskQueue} status={activeSession.status} />
          </div>

          <div className="card" style={{ flex: 1, padding: '16px', overflowY: 'auto', minHeight: '160px', maxHeight: '220px' }}>
            <h3 style={{ margin: '0 0 10px 0', fontSize: '13px', fontWeight: 600,
              display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--text-secondary)' }}>
              <Activity size={14} /> Live Event Stream
              <span style={{ marginLeft: 'auto', fontSize: '11px' }}>{taskQueue.length} events</span>
            </h3>
            <div style={{ fontSize: '12px', fontFamily: 'var(--font-mono)', display: 'flex', flexDirection: 'column', gap: '2px' }}>
              {[...taskQueue].reverse().slice(0, 30).map((task, i) => (
                <div key={i} style={{
                  padding: '3px 8px', borderRadius: '3px',
                  backgroundColor: i === 0 ? 'var(--bg-tertiary)' : 'transparent',
                  display: 'grid', gridTemplateColumns: '40px 1fr 1fr 80px', gap: '8px', alignItems: 'center'
                }}>
                  <span style={{ color: task.workstation === 'CW' ? 'var(--accent-blue)' : 'var(--accent-cyan)',
                    fontWeight: 600 }}>{task.workstation}</span>
                  <span style={{ color: 'var(--text-secondary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {task.task_label}
                  </span>
                  <span style={{ color: 'var(--text-secondary)' }}>P{task.product_id}</span>
                  <span style={{ color: task.fatigue > 0.6 ? 'var(--accent-red)' : 'var(--text-secondary)',
                    textAlign: 'right' }}>
                    HR {task.hr?.toFixed(0) ?? '—'}
                  </span>
                </div>
              ))}
              {taskQueue.length === 0 && (
                <div style={{ color: 'var(--text-secondary)', padding: '8px' }}>
                  {isActive ? 'Waiting for simulation events…' : 'No events recorded.'}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Right: parameter panel */}
        <div style={{ width: '280px', flexShrink: 0 }}>
          <ParamPanel session={activeSession} />
        </div>
      </div>
    </div>
  );
};
