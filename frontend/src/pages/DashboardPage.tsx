import React, { useEffect, useState } from 'react';
import { useSimStore } from '../store/simulationStore';
import { SimSetupModal } from '../components/common/SimSetupModal';
import { Play, Trash2, Activity, AlertTriangle, ChevronDown, ChevronRight, Eye } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import type { SimulationSession } from '../api/types';

const StatusBadge: React.FC<{ status: string }> = ({ status }) => {
  const colors: Record<string, { bg: string; text: string }> = {
    running:   { bg: 'var(--accent-green)',  text: 'white' },
    paused:    { bg: 'var(--accent-amber)',  text: 'white' },
    error:     { bg: 'var(--accent-red)',    text: 'white' },
    completed: { bg: 'var(--bg-tertiary)',   text: 'var(--text-secondary)' },
    queued:    { bg: 'var(--bg-tertiary)',   text: 'var(--text-secondary)' },
  };
  const c = colors[status] || colors.queued;
  return (
    <span style={{
      padding: '2px 8px', borderRadius: '10px', fontSize: '11px',
      fontWeight: 600, backgroundColor: c.bg, color: c.text,
      textTransform: 'uppercase', letterSpacing: '0.05em'
    }}>
      {status}
    </span>
  );
};

const SimCard: React.FC<{
  session: SimulationSession;
  onView: () => void;
  onDelete: () => void;
}> = ({ session, onView, onDelete }) => {
  const [showError, setShowError] = useState(false);

  const kpis = session.result?.kpis;
  const timeSince = session.created_at
    ? new Date(session.created_at * 1000).toLocaleTimeString()
    : '—';

  return (
    <div className="card" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <h3 style={{ margin: '0 0 4px 0', fontSize: '15px', fontWeight: 600,
            overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {session.label}
          </h3>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
            <StatusBadge status={session.status} />
            <span style={{ fontSize: '11px', color: 'var(--text-secondary)',
              padding: '2px 6px', background: 'var(--bg-tertiary)', borderRadius: '4px' }}>
              {session.mode.toUpperCase()}
            </span>
            <span style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>{timeSince}</span>
          </div>
        </div>
        <div style={{ display: 'flex', gap: '6px', flexShrink: 0 }}>
          <button onClick={onView}
            style={{ background: 'var(--bg-tertiary)', border: 'none', padding: '6px 10px',
              borderRadius: '4px', color: 'var(--accent-blue)', cursor: 'pointer',
              display: 'flex', alignItems: 'center', gap: '4px', fontSize: '12px' }}
            title="Open simulation view"
          >
            <Eye size={14} /> View
          </button>
          <button onClick={onDelete}
            style={{ background: 'var(--bg-tertiary)', border: 'none', padding: '6px',
              borderRadius: '4px', color: 'var(--accent-red)', cursor: 'pointer' }}
            title="Delete"
          >
            <Trash2 size={14} />
          </button>
        </div>
      </div>

      {/* Config summary */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px', fontSize: '12px' }}>
        {[
          ['Takt Time', `${session.config?.takt_time_seconds ?? '—'}s`],
          ['Robot Speed', `${session.config?.robot_speed_factor ?? '—'}×`],
          ['Buffer Cap', session.config?.buffer_capacity ?? '—'],
          ['CW Worker', session.config?.cw_worker_id ?? '—'],
        ].map(([label, val]) => (
          <div key={label as string} style={{ display: 'flex', justifyContent: 'space-between',
            padding: '4px 8px', background: 'var(--bg-tertiary)', borderRadius: '4px' }}>
            <span style={{ color: 'var(--text-secondary)' }}>{label}</span>
            <span style={{ fontWeight: 500 }}>{val as string}</span>
          </div>
        ))}
      </div>

      {/* Completed KPI summary */}
      {session.status === 'completed' && kpis && (
        <div style={{ borderTop: '1px solid var(--border)', paddingTop: '12px' }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '8px' }}>
            {[
              { label: 'OEE', value: kpis.oee != null ? `${(kpis.oee * 100).toFixed(1)}%` : '—' },
              { label: 'Units', value: kpis.total_units_produced ?? kpis.throughput_total ?? '—' },
              { label: 'Takt', value: kpis.takt_adherence != null ? `${(kpis.takt_adherence * 100).toFixed(0)}%` : '—' },
            ].map(({ label, value }) => (
              <div key={label} style={{ textAlign: 'center', padding: '8px',
                background: 'var(--bg-tertiary)', borderRadius: '6px' }}>
                <div style={{ fontSize: '18px', fontWeight: 700, color: 'var(--accent-blue)' }}>{value}</div>
                <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '2px' }}>{label}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Error panel */}
      {session.status === 'error' && session.error_msg && (
        <div style={{ borderTop: '1px solid var(--border)', paddingTop: '12px' }}>
          <button
            onClick={() => setShowError(v => !v)}
            style={{ background: 'none', border: 'none', cursor: 'pointer', width: '100%', padding: 0,
              color: 'var(--accent-red)', display: 'flex', alignItems: 'center', gap: '6px',
              fontSize: '12px', fontWeight: 600 }}
          >
            <AlertTriangle size={14} />
            Error — click to {showError ? 'hide' : 'expand'}
            {showError ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
          </button>
          {showError && (
            <pre style={{
              marginTop: '8px', padding: '10px', borderRadius: '4px',
              background: 'var(--status-error-bg)', color: 'var(--accent-red)',
              fontSize: '11px', fontFamily: 'var(--font-mono)',
              overflowX: 'auto', whiteSpace: 'pre-wrap', wordBreak: 'break-all',
              border: '1px solid var(--status-error-border)'
            }}>
              {session.error_msg}
            </pre>
          )}
        </div>
      )}
    </div>
  );
};

export const DashboardPage: React.FC = () => {
  const { sessions, fetchSessions, deleteSimulation } = useSimStore();
  const [showModal, setShowModal] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    fetchSessions();
    const interval = setInterval(fetchSessions, 3000);
    return () => clearInterval(interval);
  }, []);

  const running   = sessions.filter(s => s.status === 'running' || s.status === 'paused');
  const completed = sessions.filter(s => s.status === 'completed');
  const errored   = sessions.filter(s => s.status === 'error');
  const queued    = sessions.filter(s => s.status === 'queued');

  const renderGroup = (title: string, items: SimulationSession[], accent?: string) => (
    items.length > 0 && (
      <section>
        <h3 style={{ fontSize: '13px', fontWeight: 600, color: accent || 'var(--text-secondary)',
          marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ display: 'inline-block', width: '8px', height: '8px', borderRadius: '50%',
            backgroundColor: accent || 'var(--text-secondary)' }} />
          {title} ({items.length})
        </h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '16px' }}>
          {items.map(session => (
            <SimCard
              key={session.id}
              session={session}
              onView={() => navigate(`/sim/${session.id}`)}
              onDelete={() => deleteSimulation(session.id)}
            />
          ))}
        </div>
      </section>
    )
  );

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ margin: 0 }}>Dashboard</h2>
          <p style={{ color: 'var(--text-secondary)', margin: '4px 0 0 0', fontSize: '14px' }}>
            {sessions.length} simulation{sessions.length !== 1 ? 's' : ''} total
            {running.length > 0 && ` · ${running.length} active`}
            {errored.length > 0 && ` · ${errored.length} errored`}
          </p>
        </div>
        <button
          onClick={() => setShowModal(true)}
          style={{
            padding: '10px 20px', background: 'var(--accent-blue)',
            color: 'white', border: 'none', borderRadius: '6px',
            display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 600, cursor: 'pointer'
          }}
        >
          <Play size={16} fill="white" /> New Simulation
        </button>
      </div>

      {/* Groups */}
      {renderGroup('Active', running, 'var(--accent-green)')}
      {renderGroup('Queued', queued, 'var(--accent-amber)')}
      {renderGroup('Errors', errored, 'var(--accent-red)')}
      {renderGroup('Completed', completed, 'var(--text-secondary)')}

      {/* Empty state */}
      {sessions.length === 0 && (
        <div style={{ padding: '60px 40px', textAlign: 'center', color: 'var(--text-secondary)' }}>
          <Activity size={56} style={{ opacity: 0.15, marginBottom: '16px', display: 'block', margin: '0 auto 16px' }} />
          <h3 style={{ margin: '0 0 8px 0', color: 'var(--text-primary)' }}>No simulations yet</h3>
          <p style={{ margin: 0 }}>Click <strong>New Simulation</strong> to start your first run.</p>
        </div>
      )}

      {showModal && <SimSetupModal onClose={() => setShowModal(false)} />}
    </div>
  );
};
