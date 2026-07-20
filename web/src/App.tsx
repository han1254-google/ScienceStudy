import { Routes, Route, Navigate } from 'react-router-dom'
import MainLayout from './layouts/MainLayout'
import Home from './pages/Home'
import ExperimentDesign from './pages/ExperimentDesign'
import ImageAnalysis from './pages/ImageAnalysis'
import GrantWriting from './pages/GrantWriting'
import PaperWriting from './pages/PaperWriting'

function App() {
  return (
    <Routes>
      <Route path="/" element={<MainLayout />}>
        <Route index element={<Home />} />
        <Route path="experiment-design" element={<ExperimentDesign />} />
        <Route path="image-analysis" element={<ImageAnalysis />} />
        <Route path="grant-writing" element={<GrantWriting />} />
        <Route path="paper-writing" element={<PaperWriting />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default App
