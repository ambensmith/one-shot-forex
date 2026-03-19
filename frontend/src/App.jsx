import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import NewsStream from './screens/NewsStream'
import StrategyStream from './screens/StrategyStream'
import HybridBuilder from './screens/HybridBuilder'
import Dashboard from './screens/Dashboard'
import ModelComparison from './screens/ModelComparison'

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Navigate to="/news" replace />} />
        <Route path="/news" element={<NewsStream />} />
        <Route path="/strategies" element={<StrategyStream />} />
        <Route path="/hybrid" element={<HybridBuilder />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/models" element={<ModelComparison />} />
      </Routes>
    </Layout>
  )
}
