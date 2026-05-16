import React, { useState } from 'react';
import { useSimStore } from '../../store/simulationStore';
import { Play } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export const SimSetupModal: React.FC<{ onClose: () => void }> = ({ onClose }) => {
  const [label, setLabel] = useState('');
  const [mode, setMode] = useState('baseline');
  const [duration, setDuration] = useState(8.0);
  const [speed, setSpeed] = useState(0); // 0 = max speed, 1 = realtime, 60 = 1 min/sec
  
  const startSimulation = useSimStore(state => state.startSimulation);
  const navigate = useNavigate();

  const handleStart = async () => {
    try {
      const id = await startSimulation({
        label,
        mode,
        duration_hours: duration,
        speed_factor: speed
      });
      onClose();
      navigate(`/sim/${id}`);
    } catch (err) {
      console.error(err);
      alert('Failed to start simulation');
    }
  };

  return (
    <div style={{
      position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
      backgroundColor: 'rgba(0,0,0,0.5)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      zIndex: 1000
    }}>
      <div className="card" style={{ width: '400px', padding: '24px' }}>
        <h3 style={{ marginTop: 0, marginBottom: '20px' }}>Start New Simulation</h3>
        
        <div style={{ marginBottom: '16px' }}>
          <label style={{ display: 'block', marginBottom: '8px', fontSize: '14px' }}>Label (optional)</label>
          <input 
            type="text" 
            value={label} 
            onChange={e => setLabel(e.target.value)}
            style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid var(--border)' }}
            placeholder="e.g. Baseline Test 1"
          />
        </div>

        <div style={{ marginBottom: '16px' }}>
          <label style={{ display: 'block', marginBottom: '8px', fontSize: '14px' }}>Mode</label>
          <select 
            value={mode} 
            onChange={e => setMode(e.target.value)}
            style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid var(--border)' }}
          >
            <option value="baseline">Baseline (No Agent)</option>
            <option value="magi">MAGI (Cognitive Agent Active)</option>
          </select>
        </div>

        <div style={{ marginBottom: '16px', display: 'flex', gap: '16px' }}>
          <div style={{ flex: 1 }}>
            <label style={{ display: 'block', marginBottom: '8px', fontSize: '14px' }}>Duration (hours)</label>
            <input 
              type="number" 
              value={duration} 
              onChange={e => setDuration(parseFloat(e.target.value))}
              style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid var(--border)' }}
              min={0.1} step={0.5}
            />
          </div>
          <div style={{ flex: 1 }}>
            <label style={{ display: 'block', marginBottom: '8px', fontSize: '14px' }}>Speed Factor</label>
            <select 
              value={speed} 
              onChange={e => setSpeed(parseFloat(e.target.value))}
              style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid var(--border)' }}
            >
              <option value={0}>Max Speed</option>
              <option value={1}>1x (Real-time)</option>
              <option value={60}>60x (1 min/sec)</option>
              <option value={600}>600x (10 min/sec)</option>
            </select>
          </div>
        </div>

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: '24px' }}>
          <button onClick={onClose} style={{ padding: '8px 16px', border: '1px solid var(--border)', background: 'transparent', borderRadius: '4px', color: 'var(--text-primary)' }}>
            Cancel
          </button>
          <button onClick={handleStart} style={{ padding: '8px 16px', border: 'none', background: 'var(--accent-blue)', color: 'white', borderRadius: '4px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Play size={16} /> Start
          </button>
        </div>
      </div>
    </div>
  );
};
