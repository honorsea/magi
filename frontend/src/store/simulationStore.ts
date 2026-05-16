import { create } from 'zustand';
import { api } from '../api/client';
import type { SimulationSession } from '../api/types';
import { SimWebSocket } from '../api/websocket';
import { useKpiStore } from './kpiStore';

interface SimulationState {
  sessions: SimulationSession[];
  activeSessionId: string | null;
  activeSession: SimulationSession | null;
  ws: SimWebSocket | null;
  taskRecords: any[];
  physioRecords: any[];
  
  // Actions
  fetchSessions: () => Promise<void>;
  setActiveSession: (id: string | null) => Promise<void>;
  startSimulation: (params: any) => Promise<string>;
  pauseSimulation: (id: string) => Promise<void>;
  resumeSimulation: (id: string) => Promise<void>;
  stopSimulation: (id: string) => Promise<void>;
  deleteSimulation: (id: string) => Promise<void>;
}

export const useSimStore = create<SimulationState>((set, get) => ({
  sessions: [],
  activeSessionId: null,
  activeSession: null,
  ws: null,
  taskRecords: [],
  physioRecords: [],

  fetchSessions: async () => {
    try {
      const sessions = await api.sim.list();
      set({ sessions });
      
      const { activeSessionId } = get();
      if (activeSessionId) {
        const active = sessions.find(s => s.id === activeSessionId) || null;
        set({ activeSession: active });
      }
    } catch (err) {
      console.error('Failed to fetch sessions:', err);
    }
  },

  setActiveSession: async (id: string | null) => {
    const previousSessionId = get().activeSessionId;
    const currentWs = get().ws;
    if (currentWs) {
      currentWs.disconnect();
    }

    if (!id || previousSessionId !== id) {
      useKpiStore.getState().reset();
    }

    if (!id) {
      set({
        activeSessionId: null,
        activeSession: null,
        ws: null,
        taskRecords: [],
        physioRecords: []
      });
      return;
    }

    try {
      const session = await api.sim.get(id);
      const ws = new SimWebSocket(id);
      ws.connect();

      ws.onMessage((msg: any) => {
        if (msg.type === 'kpi_snapshot') {
          const kpiPayload = msg.data ?? {};
          const sim_time_s = kpiPayload.sim_time_s ?? 0;
          useKpiStore.getState().updateKpis(kpiPayload, sim_time_s);
          return;
        }

        if (msg.type === 'sim_complete' || msg.type === 'sim_stopped' || msg.type === 'sim_error') {
          get().fetchSessions();
          return;
        }

        if (msg.type === 'task_record') {
          set((state) => ({ taskRecords: [...state.taskRecords, msg.data].slice(-100) }));
          return;
        }

        if (msg.type === 'physio_record') {
          set((state) => ({ physioRecords: [...state.physioRecords, msg.data].slice(-200) }));
        }
      });
      
      set({ activeSessionId: id, activeSession: session, ws, taskRecords: [], physioRecords: [] });
      
      // Keep fetching periodically to update status
      get().fetchSessions();
    } catch (err) {
      console.error('Failed to set active session:', err);
    }
  },

  startSimulation: async (params) => {
    const res = await api.sim.start(params);
    await get().fetchSessions();
    await get().setActiveSession(res.sim_id);
    return res.sim_id;
  },

  pauseSimulation: async (id) => {
    await api.sim.pause(id);
    await get().fetchSessions();
  },

  resumeSimulation: async (id) => {
    await api.sim.resume(id);
    await get().fetchSessions();
  },

  stopSimulation: async (id) => {
    await api.sim.stop(id);
    await get().fetchSessions();
  },

  deleteSimulation: async (id) => {
    await api.sim.delete(id);
    if (get().activeSessionId === id) {
      await get().setActiveSession(null);
    }
    await get().fetchSessions();
  }
}));
