import { create } from "zustand";
import { persist } from "zustand/middleware";

interface ViewerState {
  overlayOpacity: number;
  toggleOverlayOpacity: (value: number) => void;
  selectedRegion: "WT" | "TC" | "ET";
  setSelectedRegion: (region: "WT" | "TC" | "ET") => void;
  uncertaintyVisible: boolean;
  toggleUncertainty: () => void;
}

interface SettingsState {
  theme: "light" | "dark";
  changeThreshold: number;
  confidenceThreshold: number;
  units: "ml" | "cc";
  setTheme: (theme: "light" | "dark") => void;
  setChangeThreshold: (value: number) => void;
  setConfidenceThreshold: (value: number) => void;
  setUnits: (units: "ml" | "cc") => void;
}

interface JobsState {
  jobs: Array<{ id: string; studyId: string; status: string; startedAt: string; durationSec: number }>;
  addJob: (job: JobsState["jobs"][number]) => void;
  updateJobStatus: (id: string, status: string) => void;
}

export const useViewerStore = create<ViewerState>((set) => ({
  overlayOpacity: 0.6,
  toggleOverlayOpacity: (value) => set({ overlayOpacity: value }),
  selectedRegion: "WT",
  setSelectedRegion: (region) => set({ selectedRegion: region }),
  uncertaintyVisible: false,
  toggleUncertainty: () => set((state) => ({ uncertaintyVisible: !state.uncertaintyVisible }))
}));

export const useSettingsStore = create<SettingsState>()(persist((set) => ({
  theme: "light",
  changeThreshold: 10,
  confidenceThreshold: 0.6,
  units: "ml",
  setTheme: (theme) => set({ theme }),
  setChangeThreshold: (value) => set({ changeThreshold: value }),
  setConfidenceThreshold: (value) => set({ confidenceThreshold: value }),
  setUnits: (units) => set({ units })
}), {
  name: "tx_preferences",
  skipHydration: true
}));

export const useJobsStore = create<JobsState>((set) => ({
  jobs: [],
  addJob: (job) => set((state) => ({ jobs: [...state.jobs, job] })),
  updateJobStatus: (id, status) =>
    set((state) => ({
      jobs: state.jobs.map((job) => (job.id === id ? { ...job, status } : job))
    }))
}));
