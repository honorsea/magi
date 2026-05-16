import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import { Save, RotateCcw, Palette, Server, Bot, Activity, Database, Check, AlertCircle } from 'lucide-react';

type Tab = 'branding' | 'general' | 'llm' | 'agent' | 'simulation';

// ── Reusable field components ──────────────────────────────────────────────────

const Field: React.FC<{ label: string; hint?: string; children: React.ReactNode }> = ({ label, hint, children }) => (
  <div style={{ marginBottom: '16px' }}>
    <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>{label}</label>
    {hint && <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginBottom: '6px' }}>{hint}</div>}
    {children}
  </div>
);

const TextInput: React.FC<{
  value: any; onChange: (v: string) => void; placeholder?: string; type?: string; min?: string; max?: string; step?: string
}> = ({ value, onChange, placeholder, type = 'text', min, max, step }) => (
  <input type={type} value={value ?? ''} onChange={e => onChange(e.target.value)}
    placeholder={placeholder} min={min} max={max} step={step}
    style={{ width: '100%', padding: '8px 10px', borderRadius: '6px',
      border: '1px solid var(--border)', background: 'var(--bg-secondary)',
      color: 'var(--text-primary)', fontSize: '13px', boxSizing: 'border-box' }} />
);

const Toggle: React.FC<{ value: boolean; onChange: (v: boolean) => void; label: string }> = ({ value, onChange, label }) => (
  <label style={{ display: 'flex', alignItems: 'center', gap: '10px', cursor: 'pointer' }}>
    <div
      onClick={() => onChange(!value)}
      style={{
        width: '40px', height: '22px', borderRadius: '11px', position: 'relative',
        background: value ? 'var(--accent-blue)' : 'var(--border)', transition: 'background 0.2s', cursor: 'pointer'
      }}
    >
      <div style={{
        position: 'absolute', top: '3px', width: '16px', height: '16px', borderRadius: '50%',
        background: 'white', transition: 'left 0.2s',
        left: value ? '21px' : '3px'
      }} />
    </div>
    <span style={{ fontSize: '13px' }}>{label}</span>
  </label>
);

const SelectInput: React.FC<{
  value: any; onChange: (v: string) => void; options: Array<{ value: string; label: string }>
}> = ({ value, onChange, options }) => (
  <select value={value ?? ''} onChange={e => onChange(e.target.value)}
    style={{ width: '100%', padding: '8px 10px', borderRadius: '6px',
      border: '1px solid var(--border)', background: 'var(--bg-secondary)',
      color: 'var(--text-primary)', fontSize: '13px' }}>
    {options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
  </select>
);

const Textarea: React.FC<{
  value: any; onChange: (v: string) => void; rows?: number; placeholder?: string
}> = ({ value, onChange, rows = 4, placeholder }) => (
  <textarea value={value ?? ''} onChange={e => onChange(e.target.value)} rows={rows} placeholder={placeholder}
    style={{ width: '100%', padding: '8px 10px', borderRadius: '6px',
      border: '1px solid var(--border)', background: 'var(--bg-secondary)',
      color: 'var(--text-primary)', fontSize: '13px', fontFamily: 'var(--font-mono)',
      resize: 'vertical', boxSizing: 'border-box' }} />
);

// ── Main Settings Page ─────────────────────────────────────────────────────────

export const SettingsPage: React.FC = () => {
  const [settings, setSettings] = useState<Record<string, any>>({});
  const [activeTab, setActiveTab] = useState<Tab>('branding');
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState<{ msg: string; ok: boolean } | null>(null);

  useEffect(() => { loadSettings(); }, []);

  const loadSettings = async () => {
    try {
      const res = await api.config.getSettings();
      setSettings((res as any).settings || res || {});
    } catch (err: any) {
      showToast(`Failed to load settings: ${err.message}`, false);
    }
  };

  const set = (key: string, value: any) => setSettings(prev => ({ ...prev, [key]: value }));

  const handleSave = async () => {
    setSaving(true);
    try {
      await api.config.updateSettings(settings as any);
      showToast('Settings saved', true);
    } catch (err: any) {
      showToast(`Save failed: ${err.message}`, false);
    }
    setSaving(false);
  };

  const handleReset = async () => {
    if (!confirm('Reset all settings to defaults?')) return;
    try {
      await api.config.resetSettings();
      await loadSettings();
      showToast('Settings reset to defaults', true);
    } catch (err: any) {
      showToast(`Reset failed: ${err.message}`, false);
    }
  };

  const showToast = (msg: string, ok: boolean) => {
    setToast({ msg, ok });
    setTimeout(() => setToast(null), 3000);
  };

  const TABS: Array<{ id: Tab; label: string; icon: React.ReactNode }> = [
    { id: 'branding',   label: 'Branding',    icon: <Palette size={15} /> },
    { id: 'general',    label: 'General',      icon: <Server size={15} /> },
    { id: 'llm',        label: 'LLM / AI',     icon: <Bot size={15} /> },
    { id: 'agent',      label: 'Agent',        icon: <Activity size={15} /> },
    { id: 'simulation', label: 'Simulation',   icon: <Database size={15} /> },
  ];

  return (
    <div style={{ maxWidth: '860px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ margin: 0 }}>Settings</h2>
          <p style={{ margin: '4px 0 0 0', color: 'var(--text-secondary)', fontSize: '13px' }}>
            Configure the MAGI Dashboard. All changes are persisted to SQLite.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          {toast && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px',
              color: toast.ok ? 'var(--accent-green)' : 'var(--accent-red)' }}>
              {toast.ok ? <Check size={14} /> : <AlertCircle size={14} />}
              {toast.msg}
            </div>
          )}
          <button onClick={handleReset}
            style={{ padding: '8px 14px', background: 'var(--bg-tertiary)', border: 'none',
              borderRadius: '6px', cursor: 'pointer', display: 'flex', alignItems: 'center',
              gap: '6px', fontSize: '13px', color: 'var(--text-secondary)' }}>
            <RotateCcw size={14} /> Reset
          </button>
          <button onClick={handleSave} disabled={saving}
            style={{ padding: '8px 18px', background: 'var(--accent-blue)', color: 'white',
              border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight: 600,
              display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px' }}>
            <Save size={14} /> {saving ? 'Saving…' : 'Save'}
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', borderBottom: '1px solid var(--border)', gap: '4px' }}>
        {TABS.map(tab => (
          <button key={tab.id} onClick={() => setActiveTab(tab.id)}
            style={{
              padding: '8px 16px', border: 'none', background: 'none', cursor: 'pointer',
              color: activeTab === tab.id ? 'var(--accent-blue)' : 'var(--text-secondary)',
              borderBottom: activeTab === tab.id ? '2px solid var(--accent-blue)' : '2px solid transparent',
              fontWeight: activeTab === tab.id ? 600 : 400,
              display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px',
              marginBottom: '-1px'
            }}>
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="card" style={{ padding: '28px' }}>
        {activeTab === 'branding' && (
          <>
            <Field label="Dashboard Title" hint="Shown in the sidebar and browser tab">
              <TextInput value={settings['branding.title']} onChange={v => set('branding.title', v)} placeholder="MAGI Dashboard" />
            </Field>
            <Field label="Subtitle" hint="Optional tagline shown under the title">
              <TextInput value={settings['branding.subtitle']} onChange={v => set('branding.subtitle', v)} placeholder="Silverline Assembly Line" />
            </Field>
            <Field label="Logo URL" hint="URL to a logo image (SVG or PNG). Leave empty to use default icon.">
              <TextInput value={settings['branding.logo_url']} onChange={v => set('branding.logo_url', v)} placeholder="https://example.com/logo.svg" />
            </Field>
            <Field label="Accent Color" hint="Primary brand color (CSS value, e.g. hsl(217, 91%, 50%) or #3b82f6)">
              <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                <TextInput value={settings['branding.accent_color']} onChange={v => set('branding.accent_color', v)} placeholder="hsl(217, 91%, 50%)" />
                <div style={{ width: '40px', height: '36px', borderRadius: '6px', border: '1px solid var(--border)',
                  background: settings['branding.accent_color'] || 'hsl(217,91%,50%)', flexShrink: 0 }} />
              </div>
            </Field>
            <Field label="Default Theme">
              <SelectInput value={settings['ui.theme']} onChange={v => set('ui.theme', v)}
                options={[{ value: 'light', label: 'Light (default)' }, { value: 'dark', label: 'Dark' }]} />
            </Field>
          </>
        )}

        {activeTab === 'general' && (
          <>
            <Field label="Server Host" hint="Bind address for the web server. Use 0.0.0.0 for network access.">
              <TextInput value={settings['server.host']} onChange={v => set('server.host', v)} placeholder="0.0.0.0" />
            </Field>
            <Field label="Server Port">
              <TextInput value={settings['server.port']} onChange={v => set('server.port', parseInt(v))} type="number" min="1024" max="65535" />
            </Field>
            <Field label="Output Directory" hint="Where simulation artifacts (CSVs, PNGs, traces) are saved">
              <TextInput value={settings['general.output_dir']} onChange={v => set('general.output_dir', v)} placeholder="magi_outputs" />
            </Field>
            <Field label="Default Duration (hours)">
              <TextInput value={settings['general.default_duration_hours']} onChange={v => set('general.default_duration_hours', parseFloat(v))} type="number" min="0.1" step="0.5" />
            </Field>
            <Field label="Default Replications">
              <TextInput value={settings['general.default_replications']} onChange={v => set('general.default_replications', parseInt(v))} type="number" min="1" max="100" />
            </Field>
            <Field label="Default Random Seed">
              <TextInput value={settings['general.default_seed']} onChange={v => set('general.default_seed', parseInt(v))} type="number" min="0" />
            </Field>
          </>
        )}

        {activeTab === 'llm' && (
          <>
            <Field label="Google API Key" hint="Your GOOGLE_API_KEY for Gemini. Also accepts GOOGLE_API_KEY env variable.">
              <TextInput value={settings['llm.api_key']} onChange={v => set('llm.api_key', v)} type="password" placeholder="AIzaSy…" />
            </Field>
            <Field label="Model" hint="Gemini model to use for the Cognitive Agent">
              <SelectInput
                value={settings['llm.model']}
                onChange={v => set('llm.model', v)}
                options={[
                  { value: 'gemini-2.5-flash-preview-04-17', label: 'Gemini 2.5 Flash (recommended)' },
                  { value: 'gemini-2.5-pro-preview-05-06',   label: 'Gemini 2.5 Pro (most capable)' },
                  { value: 'gemini-2.0-flash',               label: 'Gemini 2.0 Flash' },
                  { value: 'gemini-1.5-pro',                 label: 'Gemini 1.5 Pro' },
                  { value: 'gemini-1.5-flash',               label: 'Gemini 1.5 Flash' },
                ]}
              />
            </Field>
            <Field label="Temperature" hint="Generation temperature (0 = deterministic, 1 = creative). Recommended: 0.3–0.7">
              <TextInput value={settings['llm.temperature']} onChange={v => set('llm.temperature', parseFloat(v))} type="number" min="0" max="2" step="0.05" />
            </Field>
          </>
        )}

        {activeTab === 'agent' && (
          <>
            <Field label="System Prompt" hint="The base instruction given to the MAGI agent. Supports the full system prompt from AGENT_DIRECTIVES.md">
              <Textarea value={settings['agent.system_prompt']} onChange={v => set('agent.system_prompt', v)} rows={8}
                placeholder="You are MAGI, an AI manufacturing optimization agent…" />
            </Field>
            <Field label="Monitoring Cycle Interval (sim seconds)" hint="How often the agent autonomously monitors the simulation">
              <TextInput value={settings['agent.cycle_interval_sim_seconds']} onChange={v => set('agent.cycle_interval_sim_seconds', parseFloat(v))} type="number" min="60" max="3600" step="60" />
            </Field>
            <Field label="Max Tool Calls Per Cycle" hint="Maximum number of tool-use rounds per monitoring cycle">
              <TextInput value={settings['agent.max_tool_calls_per_cycle']} onChange={v => set('agent.max_tool_calls_per_cycle', parseInt(v))} type="number" min="1" max="20" />
            </Field>
            <Field label="Fatigue Alert Threshold" hint="Normalised fatigue score (0–1) that triggers a fatigue alert">
              <TextInput value={settings['agent.fatigue_alert_threshold']} onChange={v => set('agent.fatigue_alert_threshold', parseFloat(v))} type="number" min="0" max="1" step="0.05" />
            </Field>
            <Toggle value={settings['agent.auto_monitoring'] ?? true} onChange={v => set('agent.auto_monitoring', v)} label="Enable autonomous monitoring (agent runs without user prompts)" />
          </>
        )}

        {activeTab === 'simulation' && (
          <>
            <Field label="Default Robot Speed Factor" hint="Multiplier for robot arm speed [0.5, 2.0]">
              <TextInput value={settings['sim.default_robot_speed_factor']} onChange={v => set('sim.default_robot_speed_factor', parseFloat(v))} type="number" min="0.5" max="2.0" step="0.1" />
            </Field>
            <Field label="Default Takt Time (seconds)" hint="Product arrival interval [20, 300]">
              <TextInput value={settings['sim.default_takt_time_seconds']} onChange={v => set('sim.default_takt_time_seconds', parseFloat(v))} type="number" min="20" max="300" step="5" />
            </Field>
            <Field label="Default Buffer Capacity" hint="WIP buffer between stations [1, 20]">
              <TextInput value={settings['sim.default_buffer_capacity']} onChange={v => set('sim.default_buffer_capacity', parseInt(v))} type="number" min="1" max="20" />
            </Field>
            <Field label="Inter-Arrival Jitter CV" hint="Coefficient of variation for arrival time randomness [0, 0.3]">
              <TextInput value={settings['sim.default_inter_arrival_jitter_cv']} onChange={v => set('sim.default_inter_arrival_jitter_cv', parseFloat(v))} type="number" min="0" max="0.3" step="0.01" />
            </Field>
            <Field label="Default CW Worker ID" hint="Which worker is assigned to the Collaborative Workstation by default">
              <SelectInput value={settings['sim.default_cw_worker_id']} onChange={v => set('sim.default_cw_worker_id', v)}
                options={['001','002','003','004'].map(id => ({ value: id, label: `Worker ${id}` }))} />
            </Field>
            <Field label="Default MW Worker ID">
              <SelectInput value={settings['sim.default_mw_worker_id']} onChange={v => set('sim.default_mw_worker_id', v)}
                options={['001','002','003','004'].map(id => ({ value: id, label: `Worker ${id}` }))} />
            </Field>
          </>
        )}
      </div>
    </div>
  );
};
