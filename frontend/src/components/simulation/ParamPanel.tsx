import React, { useState, useEffect } from 'react';
import { api } from '../../api/client';
import type { ConfigState, SimulationSession } from '../../api/types';

export const ParamPanel: React.FC<{ session: SimulationSession }> = ({ session }) => {
  const [config, setConfig] = useState<ConfigState>(session.config);
  const [isApplying, setIsApplying] = useState(false);

  // Sync when session changes
  useEffect(() => {
    setConfig(session.config);
  }, [session.config]);

  const handleApply = async () => {
    setIsApplying(true);
    try {
      await api.config.updateLive(session.id, config);
    } catch (err) {
      console.error(err);
      alert('Failed to update config');
    }
    setIsApplying(false);
  };

  return (
    <div className="card" style={{ padding: '16px', height: '100%', display: 'flex', flexDirection: 'column' }}>
      <h3 style={{ margin: '0 0 16px 0', fontSize: '16px' }}>Parameters</h3>
      
      <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '16px' }}>
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', marginBottom: '4px' }}>
            <label>Robot Speed Factor</label>
            <span>{config.robot_speed_factor.toFixed(2)}x</span>
          </div>
          <input 
            type="range" min="0.5" max="2.0" step="0.05"
            value={config.robot_speed_factor}
            onChange={e => setConfig({...config, robot_speed_factor: parseFloat(e.target.value)})}
            style={{ width: '100%' }}
            disabled={session.status !== 'running' && session.status !== 'paused'}
          />
        </div>

        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', marginBottom: '4px' }}>
            <label>Takt Time (sec)</label>
            <span>{config.takt_time_seconds}s</span>
          </div>
          <input 
            type="range" min="30" max="120" step="1"
            value={config.takt_time_seconds}
            onChange={e => setConfig({...config, takt_time_seconds: parseFloat(e.target.value)})}
            style={{ width: '100%' }}
            disabled={session.status !== 'running' && session.status !== 'paused'}
          />
        </div>

        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', marginBottom: '4px' }}>
            <label>Buffer Capacity</label>
            <span>{config.buffer_capacity} units</span>
          </div>
          <input 
            type="range" min="1" max="20" step="1"
            value={config.buffer_capacity}
            onChange={e => setConfig({...config, buffer_capacity: parseInt(e.target.value)})}
            style={{ width: '100%' }}
            disabled={session.status !== 'running' && session.status !== 'paused'}
          />
        </div>

        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', marginBottom: '4px' }}>
            <label>Inter-arrival Jitter CV</label>
            <span>{config.inter_arrival_jitter_cv.toFixed(2)}</span>
          </div>
          <input 
            type="range" min="0" max="0.5" step="0.01"
            value={config.inter_arrival_jitter_cv}
            onChange={e => setConfig({...config, inter_arrival_jitter_cv: parseFloat(e.target.value)})}
            style={{ width: '100%' }}
            disabled={session.status !== 'running' && session.status !== 'paused'}
          />
        </div>
      </div>

      <button 
        onClick={handleApply}
        disabled={isApplying || (session.status !== 'running' && session.status !== 'paused')}
        style={{ 
          marginTop: '16px', 
          padding: '10px', 
          background: 'var(--accent-blue)', 
          color: 'white', 
          border: 'none', 
          borderRadius: '4px',
          opacity: (session.status !== 'running' && session.status !== 'paused') ? 0.5 : 1
        }}
      >
        {isApplying ? 'Applying...' : 'Apply Interventions'}
      </button>
    </div>
  );
};
