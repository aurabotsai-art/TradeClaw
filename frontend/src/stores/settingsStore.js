import { create } from 'zustand';

export const useSettingsStore = create((set) => ({
  panelOpen: false,
  togglePanel: () => set((state) => ({ panelOpen: !state.panelOpen })),
}));

