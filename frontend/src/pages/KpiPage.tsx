import React, { useEffect } from 'react';
import { useKpiStore } from '../store/kpiStore';
import { useSimStore } from '../store/simulationStore';
import { GaugeCard } from '../components/kpi/GaugeCard';
import { TimeSeriesChart } from '../components/kpi/TimeSeriesChart';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

export const KpiPage: React.FC = () => {
  const { currentKpis, history } = useKpiStore();
  const { activeSession, fetchSessions } = useSimStore();

  useEffect(() => {
    fetchSessions();
  }, []);

  if (!activeSession) {
    return <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-secondary)' }}>No active simulation selected. Please select one from the Dashboard.</div>;
  }

  // Flatten history for charts
  const chartData = history.map(h => ({
    sim_time_s: h.sim_time_s,
    takt_adherence: h.kpis.takt_adherence,
    throughput: h.kpis.throughput_total,
    cw_hr: h.kpis.cw_hr_mean,
    mw_hr: h.kpis.mw_hr_mean,
    cw_fatigue: h.kpis.cw_fatigue_mean,
    mw_fatigue: h.kpis.mw_fatigue_mean,
  }));

  const utilData = currentKpis ? [
    { name: 'CW Worker', utilization: currentKpis.cw_utilization * 100 },
    { name: 'MW Worker', utilization: currentKpis.mw_utilization * 100 },
    { name: 'Robot Arm', utilization: currentKpis.robot_utilization * 100 },
  ] : [];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      <div>
        <h2 style={{ margin: 0 }}>KPI Dashboard</h2>
        <p style={{ color: 'var(--text-secondary)', margin: '4px 0 0 0' }}>
          Live metrics for {activeSession.label || `Simulation ${activeSession.id}`}
        </p>
      </div>

      {!currentKpis ? (
        <div className="card" style={{ padding: '40px', textAlign: 'center', color: 'var(--text-secondary)' }}>
          Waiting for KPI data...
        </div>
      ) : (
        <>
          {/* Top Row: Gauges */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '20px' }}>
            <GaugeCard 
              title="Overall Equipment Effectiveness (OEE)" 
              value={currentKpis.oee * 100} max={100} unit="%" color="var(--accent-blue)" 
            />
            <GaugeCard 
              title="Line Balance Ratio" 
              value={currentKpis.line_balance_ratio * 100} max={100} unit="%" color="var(--accent-cyan)" 
            />
            <GaugeCard 
              title="Takt Adherence" 
              value={currentKpis.takt_adherence * 100} max={100} unit="%" color="var(--accent-green)" 
            />
            <div className="card" style={{ padding: '20px', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
              <h3 style={{ margin: '0 0 8px 0', fontSize: '14px', color: 'var(--text-secondary)' }}>Total Throughput</h3>
              <div style={{ fontSize: '36px', fontWeight: 700, color: 'var(--text-primary)' }}>{currentKpis.throughput_total}</div>
              <div style={{ fontSize: '12px', color: 'var(--accent-red)' }}>{currentKpis.throughput_dropped} dropped</div>
            </div>
          </div>

          {/* Middle Row: Ergonomics / Fatigue */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
            <TimeSeriesChart 
              title="CW Worker Fatigue & Heart Rate"
              data={chartData}
              dataKey="cw_hr"
              color="var(--accent-red)"
              yDomain={[60, 140]}
            />
            <TimeSeriesChart 
              title="MW Worker Fatigue & Heart Rate"
              data={chartData}
              dataKey="mw_hr"
              color="var(--accent-amber)"
              yDomain={[60, 140]}
            />
          </div>

          {/* Bottom Row: Utilization and Throughput */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '20px' }}>
            <div className="card" style={{ padding: '20px', height: '300px', display: 'flex', flexDirection: 'column' }}>
              <h3 style={{ margin: '0 0 16px 0', fontSize: '14px', color: 'var(--text-secondary)' }}>Resource Utilization</h3>
              <div style={{ flex: 1, minHeight: 0 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={utilData} layout="vertical" margin={{ top: 5, right: 30, left: 40, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="var(--border)" />
                    <XAxis type="number" domain={[0, 100]} stroke="var(--text-secondary)" fontSize={12} />
                    <YAxis dataKey="name" type="category" stroke="var(--text-secondary)" fontSize={12} />
                    <Tooltip contentStyle={{ backgroundColor: 'var(--bg-secondary)', border: '1px solid var(--border)' }} />
                    <Bar dataKey="utilization" fill="var(--accent-blue)" radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            <TimeSeriesChart 
              title="Takt Adherence Over Time"
              data={chartData}
              dataKey="takt_adherence"
              color="var(--accent-green)"
              yDomain={[0, 1.2]}
            />
          </div>
        </>
      )}
    </div>
  );
};
