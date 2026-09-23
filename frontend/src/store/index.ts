import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { CloudMetrics, OptimizationScores } from '../types'

export interface Notification {
  id: string
  title: string
  body: string
  priority: 'critical' | 'high' | 'medium' | 'low'
  timestamp: number
  read: boolean
}

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

  // Sidebar collapsed (icon-rail mode)
  sidebarCollapsed: boolean
  setSidebarCollapsed: (v: boolean) => void
  toggleSidebarCollapsed: () => void

  // Notification panel
  notifPanelOpen: boolean
  setNotifPanelOpen: (v: boolean) => void
  notifications: Notification[]
  addNotification: (n: Omit<Notification, 'id' | 'timestamp' | 'read'>) => void
  markNotifRead: (id: string) => void
  clearNotifications: () => void
}

export const useAppStore = create<AppStore>()(
  persist(
    (set) => ({
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

      sidebarCollapsed: false,
      setSidebarCollapsed: (sidebarCollapsed) => set({ sidebarCollapsed }),
      toggleSidebarCollapsed: () =>
        set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),

      notifPanelOpen: false,
      setNotifPanelOpen: (notifPanelOpen) => set({ notifPanelOpen }),
      notifications: [],
      addNotification: (n) =>
        set((s) => ({
          notifications: [
            { ...n, id: Math.random().toString(36).slice(2), timestamp: Date.now(), read: false },
            ...s.notifications.slice(0, 49),
          ],
        })),
      markNotifRead: (id) =>
        set((s) => ({
          notifications: s.notifications.map((n) =>
            n.id === id ? { ...n, read: true } : n
          ),
        })),
      clearNotifications: () => set({ notifications: [] }),
    }),
    {
      name: 'greenmind-ui',
      partialize: (s) => ({ sidebarCollapsed: s.sidebarCollapsed }),
    }
  )
)
