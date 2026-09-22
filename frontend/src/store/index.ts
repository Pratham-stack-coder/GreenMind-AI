import { create } from 'zustand'
import type { CloudMetrics, OptimizationScores } from '../types'

interface AppStore {
  // Provider/region selection
  provider: string
  region: string
  setProvider: (p: string) => void
  setRegion: (r: string) => void

  // Live metrics
  liveMetrics: CloudMetrics | null
  setLiveMetrics: (m: CloudMetrics) => void

  // Scores
  scores: OptimizationScores | null
  setScores: (s: OptimizationScores) => void

  // UI
  sidebarOpen: boolean
  setSidebarOpen: (v: boolean) => void
}

export const useAppStore = create<AppStore>((set) => ({
  provider: 'aws',
  region: 'us-east',
  setProvider: (provider) => set({ provider }),
  setRegion: (region) => set({ region }),

  liveMetrics: null,
  setLiveMetrics: (liveMetrics) => set({ liveMetrics }),

  scores: null,
  setScores: (scores) => set({ scores }),

  sidebarOpen: true,
  setSidebarOpen: (sidebarOpen) => set({ sidebarOpen }),
}))
