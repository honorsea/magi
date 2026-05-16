import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

interface TimeSeriesProps {
  title: string;
  data: any[];
  dataKey: string;
  color: string;
  yDomain?: [number, number];
}

export const TimeSeriesChart: React.FC<TimeSeriesProps> = ({ title, data, dataKey, color, yDomain }) => {
  return (
    <div className="card" style={{ padding: '20px', height: '300px', display: 'flex', flexDirection: 'column' }}>
      <h3 style={{ margin: '0 0 16px 0', fontSize: '14px', color: 'var(--text-secondary)' }}>{title}</h3>
      <div style={{ flex: 1, minHeight: 0 }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border)" />
            <XAxis 
              dataKey="sim_time_s" 
              type="number"
              domain={['dataMin', 'dataMax']}
              tickFormatter={(val) => `${Math.floor(val / 60)}m`}
              stroke="var(--text-secondary)"
              fontSize={12}
              tickLine={false}
            />
            <YAxis 
              domain={yDomain || ['auto', 'auto']}
              stroke="var(--text-secondary)"
              fontSize={12}
              tickLine={false}
              axisLine={false}
            />
            <Tooltip 
              contentStyle={{ backgroundColor: 'var(--bg-secondary)', border: '1px solid var(--border)', borderRadius: '4px' }}
              labelFormatter={(val) => `Time: ${(val as number).toFixed(1)}s`}
            />
            <Line 
              type="monotone" 
              dataKey={dataKey} 
              stroke={color} 
              strokeWidth={2} 
              dot={false}
              isAnimationActive={false} // better performance for real-time
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};
