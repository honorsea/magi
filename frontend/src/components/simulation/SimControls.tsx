import React from 'react';
import { useSimStore } from '../../store/simulationStore';
import { Play, Pause, Square } from 'lucide-react';
import type { SimulationSession } from '../../api/types';

export const SimControls: React.FC<{ session: SimulationSession }> = ({ session }) => {
  const { pauseSimulation, resumeSimulation, stopSimulation } = useSimStore();

  return (
    <div className="card" style={{ display: 'flex', gap: '8px', padding: '8px' }}>
      {session.status === 'paused' ? (
        <button 
          onClick={() => resumeSimulation(session.id)}
          style={{ background: 'var(--accent-green)', color: 'white', border: 'none', padding: '8px 16px', borderRadius: '4px', display: 'flex', alignItems: 'center', gap: '6px' }}
        >
          <Play size={16} /> Resume
        </button>
      ) : (
        <button 
          onClick={() => pauseSimulation(session.id)}
          disabled={session.status !== 'running'}
          style={{ background: 'var(--bg-tertiary)', color: 'var(--text-primary)', border: 'none', padding: '8px 16px', borderRadius: '4px', display: 'flex', alignItems: 'center', gap: '6px', opacity: session.status !== 'running' ? 0.5 : 1 }}
        >
          <Pause size={16} /> Pause
        </button>
      )}

      <button 
        onClick={() => stopSimulation(session.id)}
        disabled={session.status === 'completed' || session.status === 'error'}
        style={{ background: 'var(--bg-tertiary)', color: 'var(--accent-red)', border: 'none', padding: '8px 16px', borderRadius: '4px', display: 'flex', alignItems: 'center', gap: '6px', opacity: (session.status === 'completed' || session.status === 'error') ? 0.5 : 1 }}
      >
        <Square size={16} /> Stop
      </button>
    </div>
  );
};
