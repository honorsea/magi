import { create } from 'zustand';
import { api } from '../api/client';
import type { SimulationSession } from '../api/types';
import { SimWebSocket } from '../api/websocket';

interface SimulationState {
  sessions: SimulationSession[];
  activeSessionId: string | null;
  activeSession: SimulationSession | null;
  ws: SimWebSocket | null;
  
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
    const currentWs = get().ws;
    if (currentWs) {
      currentWs.disconnect();
    }

    if (!id) {
      set({ activeSessionId: null, activeSession: null, ws: null });
      return;
    }

    try {
      const session = await api.sim.get(id);
      const ws = new SimWebSocket(id);
      ws.connect();
      
      set({ activeSessionId: id, activeSession: session, ws });
      
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
