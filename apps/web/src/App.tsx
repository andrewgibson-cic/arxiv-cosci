import { Routes, Route } from 'react-router-dom'
import { Home } from './pages/Home'
import { Search } from './pages/Search'
import { PaperDetail } from './pages/PaperDetail'
import { GraphView } from './pages/GraphView'
import { Layout } from './components/Layout'

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/search" element={<Search />} />
        <Route path="/paper/:arxivId" element={<PaperDetail />} />
        <Route path="/graph/:arxivId?" element={<GraphView />} />
      </Routes>
    </Layout>
  )
}

export default App