import { Routes, Route } from 'react-router-dom'
import { Home } from './pages/Home'
import { Search } from './pages/Search'
import { PaperDetail } from './pages/PaperDetail'
import { GraphView } from './pages/GraphView'
import { GraphViewV2 } from './pages/GraphViewV2'
import { Layout } from './components/Layout'

function App() {
  return (
    <>
      <Routes>
        {/* Routes that need Layout wrapper */}
        <Route element={<Layout><Home /></Layout>} path="/" />
        <Route element={<Layout><Search /></Layout>} path="/search" />
        <Route element={<Layout><PaperDetail /></Layout>} path="/paper/:arxivId" />
        <Route element={<Layout><GraphView /></Layout>} path="/graph-old/:arxivId?" />
        
        {/* GraphViewV2 - fullscreen, no layout */}
        <Route path="/graph/:arxivId?" element={<GraphViewV2 />} />
      </Routes>
    </>
  )
}

export default App
