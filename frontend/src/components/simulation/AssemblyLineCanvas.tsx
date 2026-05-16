import React, { useEffect, useRef } from 'react';

interface CanvasProps {
  events: any[];
  status?: string;
}

// Station definitions
const STATIONS = [
  { id: 'cw', label: 'CW Station', sub: 'Collaborative Workstation', x: 0.28 },
  { id: 'mw', label: 'MW Station', sub: 'Manual Workstation',        x: 0.72 },
];

const PHASE_COLORS: Record<string, string> = {
  '01_pick_fix1':     '#3b82f6',
  '02_visual_check':  '#8b5cf6',
  '03_pick_fix2':     '#3b82f6',
  '04_grounding_test':'#8b5cf6',
  '05_pick_leave':    '#3b82f6',
  '06_filter_assembly':'#22c55e',
  '07_bag_leave':     '#22c55e',
};

export const AssemblyLineCanvas: React.FC<CanvasProps> = ({ events, status = 'running' }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animRef   = useRef<number>(0);
  const timeRef   = useRef<number>(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const latest = events.length > 0 ? events[events.length - 1] : null;
    const isActive = status === 'running' || status === 'paused';

    const render = () => {
      if (isActive) timeRef.current += 0.04;

      // Resize to container
      const rect = canvas.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;
      if (canvas.width !== rect.width * dpr) {
        canvas.width  = rect.width  * dpr;
        canvas.height = rect.height * dpr;
        ctx.scale(dpr, dpr);
      }
      const W = rect.width;
      const H = rect.height;
      const t = timeRef.current;

      // Background
      ctx.clearRect(0, 0, W, H);
      ctx.fillStyle = getComputedStyle(canvas).getPropertyValue('--bg-secondary').trim() || '#fff';
      ctx.fillRect(0, 0, W, H);

      const midY = H / 2;
      const conveyorH = 32;

      // ── Conveyor belt ────────────────────────────────────────────────────
      const convStart = W * 0.05;
      const convEnd   = W * 0.95;

      ctx.fillStyle = '#e2e8f0';
      ctx.beginPath();
      ctx.roundRect(convStart, midY - conveyorH / 2, convEnd - convStart, conveyorH, 6);
      ctx.fill();

      // Animated stripes
      ctx.save();
      ctx.beginPath();
      ctx.roundRect(convStart, midY - conveyorH / 2, convEnd - convStart, conveyorH, 6);
      ctx.clip();
      ctx.strokeStyle = '#cbd5e1';
      ctx.lineWidth = 2;
      const stripeSpacing = 50;
      const offset = (t * (isActive ? 15 : 0)) % stripeSpacing;
      for (let x = convStart - stripeSpacing + offset; x < convEnd + stripeSpacing; x += stripeSpacing) {
        ctx.beginPath();
        ctx.moveTo(x, midY - conveyorH / 2);
        ctx.lineTo(x + 20, midY + conveyorH / 2);
        ctx.stroke();
      }
      ctx.restore();

      // ── Products on belt ─────────────────────────────────────────────────
      if (latest && isActive) {
        // Animate a product between stations
        const pct = (Math.sin(t * 0.5) + 1) / 2;
        const cwX  = W * STATIONS[0].x;
        const mwX  = W * STATIONS[1].x;
        const px   = cwX + (mwX - cwX) * pct;

        ctx.fillStyle = '#f97316';
        ctx.strokeStyle = '#ea580c';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.roundRect(px - 18, midY - 12, 36, 24, 4);
        ctx.fill();
        ctx.stroke();

        ctx.fillStyle = 'white';
        ctx.font = '10px sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(`P${latest?.product_id ?? ''}`, px, midY);
      }

      // ── Stations ─────────────────────────────────────────────────────────
      STATIONS.forEach(station => {
        const sx = W * station.x;
        const sW = Math.min(150, W * 0.22);
        const sH = 120;
        const sY = midY - sH / 2 - 10;

        const isActive_station = latest?.workstation === station.id.toUpperCase();
        const phaseColor = isActive_station
          ? (PHASE_COLORS[latest?.task_label] ?? '#3b82f6')
          : '#94a3b8';

        // Station box
        ctx.fillStyle = '#f8fafc';
        ctx.strokeStyle = isActive_station ? phaseColor : '#e2e8f0';
        ctx.lineWidth = isActive_station ? 2.5 : 1.5;
        ctx.shadowColor = isActive_station ? phaseColor + '44' : 'transparent';
        ctx.shadowBlur = isActive_station ? 12 : 0;
        ctx.beginPath();
        ctx.roundRect(sx - sW / 2, sY, sW, sH, 8);
        ctx.fill();
        ctx.stroke();
        ctx.shadowBlur = 0;

        // Station header bar
        ctx.fillStyle = isActive_station ? phaseColor : '#e2e8f0';
        ctx.beginPath();
        ctx.roundRect(sx - sW / 2, sY, sW, 28, { upperLeft: 8, upperRight: 8, lowerLeft: 0, lowerRight: 0 } as any);
        ctx.fill();

        ctx.fillStyle = isActive_station ? 'white' : '#64748b';
        ctx.font = `bold 12px sans-serif`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(station.label, sx, sY + 14);

        // Sub label
        ctx.fillStyle = '#94a3b8';
        ctx.font = '10px sans-serif';
        ctx.fillText(station.sub, sx, sY + 44);

        // Active phase label
        if (isActive_station && latest?.task_label) {
          ctx.fillStyle = phaseColor;
          ctx.font = 'bold 11px sans-serif';
          ctx.fillText(latest.task_label, sx, sY + 66);

          // HR indicator
          if (latest.hr != null) {
            const hrColor = latest.hr > 110 ? '#ef4444' : latest.hr > 95 ? '#f97316' : '#22c55e';
            ctx.fillStyle = hrColor;
            ctx.font = 'bold 13px sans-serif';
            ctx.fillText(`♥ ${Math.round(latest.hr)} BPM`, sx, sY + 88);
          }
        }

        // Worker icon
        const iconY = midY + conveyorH / 2 + 20;
        ctx.fillStyle = isActive_station ? phaseColor : '#cbd5e1';
        ctx.beginPath();
        ctx.arc(sx, iconY + 10, 10, 0, Math.PI * 2);
        ctx.fill();
        ctx.beginPath();
        ctx.arc(sx, iconY + 30, 14, 0, Math.PI, true);
        ctx.fill();
      });

      // ── Robot arm (between stations) ─────────────────────────────────────
      const robotX = W * 0.5;
      const isRobot = latest?.is_robot === true;
      ctx.strokeStyle = isRobot ? '#8b5cf6' : '#cbd5e1';
      ctx.lineWidth = isRobot ? 3 : 2;
      ctx.shadowColor = isRobot ? '#8b5cf644' : 'transparent';
      ctx.shadowBlur = isRobot ? 10 : 0;
      ctx.beginPath();
      ctx.moveTo(robotX, midY - 60);
      ctx.lineTo(robotX, midY - 20);
      ctx.stroke();
      ctx.shadowBlur = 0;
      ctx.fillStyle = isRobot ? '#8b5cf6' : '#e2e8f0';
      ctx.strokeStyle = isRobot ? '#7c3aed' : '#cbd5e1';
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.roundRect(robotX - 16, midY - 80, 32, 22, 4);
      ctx.fill();
      ctx.stroke();
      ctx.fillStyle = isRobot ? 'white' : '#94a3b8';
      ctx.font = 'bold 9px sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText('ROBOT', robotX, midY - 69);

      // ── Status overlay ────────────────────────────────────────────────────
      if (!isActive) {
        ctx.fillStyle = 'rgba(255,255,255,0.75)';
        ctx.fillRect(0, 0, W, H);
        ctx.fillStyle = '#64748b';
        ctx.font = 'bold 16px sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(
          status === 'completed' ? '✓ Simulation Completed' :
          status === 'error'     ? '⚠ Simulation Error'    :
          status === 'queued'    ? '… Queued'               : status,
          W / 2, H / 2
        );
      }

      if (isActive) {
        animRef.current = requestAnimationFrame(render);
      }
    };

    render();

    return () => cancelAnimationFrame(animRef.current);
  }, [events, status]);

  return (
    <canvas
      ref={canvasRef}
      style={{ width: '100%', height: '100%', display: 'block' }}
    />
  );
};
