import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './screens/Dashboard'
import LLMAnalysis from './screens/LLMAnalysis'
import Strategies from './screens/Strategies'
import Settings from './screens/Settings'

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/llm" element={<LLMAnalysis />} />
        <Route path="/strategies" element={<Strategies />} />
        <Route path="/settings" element={<Settings />} />
      </Routes>
    </Layout>
  )
}
