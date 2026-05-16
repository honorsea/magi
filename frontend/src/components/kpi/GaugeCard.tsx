import React from 'react';

interface GaugeProps {
  title: string;
  value: number;
  max: number;
  unit?: string;
  color: string;
  format?: (v: number) => string;
}

export const GaugeCard: React.FC<GaugeProps> = ({ title, value, max, unit = '', color, format }) => {
  const percentage = Math.min(Math.max((value / max) * 100, 0), 100);
  const displayValue = format ? format(value) : value.toFixed(1);

  return (
    <div className="card" style={{ padding: '20px', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
      <h3 style={{ margin: '0 0 16px 0', fontSize: '14px', color: 'var(--text-secondary)' }}>{title}</h3>
      
      <div style={{ position: 'relative', width: '120px', height: '60px', overflow: 'hidden' }}>
        {/* Background arc */}
        <div style={{
          position: 'absolute', top: 0, left: 0, width: '120px', height: '120px',
          borderRadius: '50%', border: '10px solid var(--bg-tertiary)',
          boxSizing: 'border-box'
        }} />
        
        {/* Foreground arc (clipped by parent height) */}
        <div style={{
          position: 'absolute', top: 0, left: 0, width: '120px', height: '120px',
          borderRadius: '50%', border: `10px solid ${color}`,
          borderBottomColor: 'transparent', borderRightColor: 'transparent',
          boxSizing: 'border-box',
          transform: `rotate(${percentage * 1.8 - 45}deg)`,
          transition: 'transform 0.5s ease-out'
        }} />
      </div>
      
      <div style={{ marginTop: '8px', textAlign: 'center' }}>
        <div style={{ fontSize: '24px', fontWeight: 700, color: 'var(--text-primary)' }}>
          {displayValue}{unit}
        </div>
      </div>
    </div>
  );
};
