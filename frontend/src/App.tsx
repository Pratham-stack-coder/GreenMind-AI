import { Routes, Route } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import Sidebar from './components/Layout/Sidebar'
import TopBar from './components/Layout/TopBar'
import DashboardPage from './pages/DashboardPage'
import PredictionsPage from './pages/PredictionsPage'
import RecommendationsPage from './pages/RecommendationsPage'
import AgentsPage from './pages/AgentsPage'
import DigitalTwinPage from './pages/DigitalTwinPage'
import CopilotPage from './pages/CopilotPage'
import AnalyticsPage from './pages/AnalyticsPage'
import SettingsPage from './pages/SettingsPage'

const pageTransition = {
  initial: { opacity: 0, y: 12 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -8 },
  transition: { duration: 0.25 },
}

export default function App() {
  return (
    <div className="main-layout">
      <Sidebar />
      <div className="content-area">
        <TopBar />
        <main className="page-content">
          <AnimatePresence mode="wait">
            <Routes>
              <Route path="/" element={<motion.div {...pageTransition}><DashboardPage /></motion.div>} />
              <Route path="/predictions" element={<motion.div {...pageTransition}><PredictionsPage /></motion.div>} />
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
