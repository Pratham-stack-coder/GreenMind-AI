import React from 'react'
import { Routes, Route } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import Sidebar from './components/Layout/Sidebar'
import TopBar from './components/Layout/TopBar'
import NotificationsPanel from './components/Layout/NotificationsPanel'
import DashboardPage from './pages/DashboardPage'
import CloudResourcesPage from './pages/CloudResourcesPage'
import PredictionsPage from './pages/PredictionsPage'
import CostOptimizationPage from './pages/CostOptimizationPage'
import CarbonIntelligencePage from './pages/CarbonIntelligencePage'
import RecommendationsPage from './pages/RecommendationsPage'
import AgentsPage from './pages/AgentsPage'
import DigitalTwinPage from './pages/DigitalTwinPage'
import CopilotPage from './pages/CopilotPage'
import AnalyticsPage from './pages/AnalyticsPage'
import SettingsPage from './pages/SettingsPage'
import { useAppStore } from './store'

const pageTransition = {
  initial: { opacity: 0, y: 12 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -8 },
  transition: { duration: 0.25 },
}

export default function App() {
  const { sidebarCollapsed } = useAppStore()
  const sidebarWidth = sidebarCollapsed ? 64 : 240

  return (
    <div
      className="main-layout"
      style={{ '--sidebar-width': `${sidebarWidth}px` } as React.CSSProperties}
    >
      <Sidebar />
      <div className="content-area">
        <TopBar />
        <NotificationsPanel />
        <main className="page-content">
          <AnimatePresence mode="wait">
            <Routes>
              <Route path="/" element={<motion.div {...pageTransition}><DashboardPage /></motion.div>} />
              <Route path="/cloud-resources" element={<motion.div {...pageTransition}><CloudResourcesPage /></motion.div>} />
              <Route path="/predictions" element={<motion.div {...pageTransition}><PredictionsPage /></motion.div>} />
              <Route path="/cost-optimization" element={<motion.div {...pageTransition}><CostOptimizationPage /></motion.div>} />
              <Route path="/carbon-intelligence" element={<motion.div {...pageTransition}><CarbonIntelligencePage /></motion.div>} />
              <Route path="/recommendations" element={<motion.div {...pageTransition}><RecommendationsPage /></motion.div>} />
              <Route path="/agents" element={<motion.div {...pageTransition}><AgentsPage /></motion.div>} />
              <Route path="/digital-twin" element={<motion.div {...pageTransition}><DigitalTwinPage /></motion.div>} />
              <Route path="/copilot" element={<motion.div {...pageTransition}><CopilotPage /></motion.div>} />
              <Route path="/analytics" element={<motion.div {...pageTransition}><AnalyticsPage /></motion.div>} />
              <Route path="/settings" element={<motion.div {...pageTransition}><SettingsPage /></motion.div>} />
            </Routes>
          </AnimatePresence>
        </main>
      </div>
    </div>
  )
}
