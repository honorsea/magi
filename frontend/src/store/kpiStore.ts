import { create } from 'zustand';

interface KpiState {
  currentKpis: Record<string, any> | null;
  history: { sim_time_s: number; kpis: Record<string, any> }[];
  
  // Actions
  updateKpis: (kpis: Record<string, any>, sim_time_s: number) => void;
  reset: () => void;
}

export const useKpiStore = create<KpiState>((set) => ({
  currentKpis: null,
  history: [],

  updateKpis: (kpis, sim_time_s) => set((state) => {
    // Only keep last 100 snapshots for memory
    const newHistory = [...state.history, { sim_time_s, kpis }].slice(-100);
    return {
      currentKpis: kpis,
      history: newHistory
    };
  }),

  reset: () => set({ currentKpis: null, history: [] })
}));
