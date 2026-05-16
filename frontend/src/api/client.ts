import type { SimulationSession, ConfigState, Settings } from './types';

const API_BASE = '/api';

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });

  if (!response.ok) {
    const errorBody = await response.text();
    throw new Error(`API Error (${response.status}): ${errorBody}`);
  }

  return response.json();
}

export const api = {
  // Simulation
  sim: {
    start: (params: { label?: string; mode?: string; duration_hours?: number; speed_factor?: number; seed?: number }) =>
      request<{ sim_id: string; status: string; message: string }>('/sim/run', {
        method: 'POST',
        body: JSON.stringify(params)
      }),
    list: () => request<SimulationSession[]>('/sim/sessions'),
    get: (id: string) => request<SimulationSession>(`/sim/${id}`),
    pause: (id: string) => request(`/sim/${id}/pause`, { method: 'POST' }),
    resume: (id: string) => request(`/sim/${id}/resume`, { method: 'POST' }),
    stop: (id: string) => request(`/sim/${id}/stop`, { method: 'POST' }),
    delete: (id: string) => request(`/sim/${id}`, { method: 'DELETE' }),
  },

  // Config
  config: {
    getLive: (sim_id: string) => request<{ config: ConfigState }>(`/config/${sim_id}/config`),
    updateLive: (sim_id: string, updates: Partial<ConfigState>) =>
      request(`/config/${sim_id}/config`, { method: 'PUT', body: JSON.stringify({ updates }) }),
    getSettings: () => request<{ settings: Settings }>('/config/settings'),
    updateSettings: (updates: Settings) =>
      request('/config/settings', { method: 'PUT', body: JSON.stringify({ updates }) }),
    resetSettings: () => request('/config/settings/reset', { method: 'POST' }),
  },

  // Agent
  agent: {
    sendMessage: (sim_id: string, message: string) =>
      request<{ status: string; message: string; queued: boolean }>(`/agent/${sim_id}/message`, {
        method: 'POST',
        body: JSON.stringify({ message }),
      }),
    getTrace: (sim_id: string) => request<{ sim_id: string; traces: any[] }>(`/agent/${sim_id}/trace`),
    listTools: (sim_id: string) => request<{ tools: any[] }>(`/agent/${sim_id}/tools`),
    listModels: () => request<{ models: any[] }>('/agent/models'),
  },

  // Shortcuts
  shortcuts: {
    list: () => request<any[]>('/shortcuts/'),
    create: (data: { name: string; category: string; description: string; content: string }) =>
      request('/shortcuts/', { method: 'POST', body: JSON.stringify(data) }),
    update: (id: string, data: { name: string; category: string; description: string; content: string }) =>
      request(`/shortcuts/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
    delete: (id: string) => request(`/shortcuts/${id}`, { method: 'DELETE' }),
    seedDefaults: () => request('/shortcuts/seed-defaults', { method: 'POST' }),
  },

  // Outputs
  outputs: {
    list: (subdir?: string) => request<any[]>(`/outputs/${subdir ? `?subdir=${subdir}` : ''}`),
    downloadUrl: (path: string) => `/api/outputs/download/${path}`,
    preview: (path: string) => request<{ name: string; content: string; truncated: boolean }>(`/outputs/preview/${path}`),
    delete: (path: string) => request(`/outputs/${path}`, { method: 'DELETE' }),
  },

  // Lean KG
  lean: {
    getGraph: () => request<{ nodes: any[]; edges: any[]; meta: any }>('/lean/graph'),
    listMethods: () => request<{ methods: any[] }>('/lean/methods'),
    getMethod: (id: string) => request<any>(`/lean/method/${id}`),
    listProblems: () => request<{ problems: any[] }>('/lean/problems'),
    queryByKpis: (kpis: Record<string, number>, baseline?: Record<string, number>, top_n = 5) =>
      request<{ triggered: any[]; count: number }>('/lean/query', {
        method: 'POST',
        body: JSON.stringify({ kpis, baseline_kpis: baseline, top_n }),
      }),
    search: (q: string) => request<{ results: any[] }>(`/lean/search?q=${encodeURIComponent(q)}`),
  },
};
