import { Link } from 'react-router-dom';
import { Search, Home, Network, Lightbulb } from 'lucide-react';

interface LayoutProps {
  children: React.ReactNode;
}

export function Layout({ children }: LayoutProps) {
  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="bg-gray-900 text-white shadow-lg">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <Link to="/" className="flex items-center space-x-2">
              <Lightbulb className="w-8 h-8 text-blue-400" />
              <h1 className="text-2xl font-bold">ArXiv Co-Scientist</h1>
            </Link>
            
            <nav className="flex items-center space-x-6">
              <Link
                to="/"
                className="flex items-center space-x-1 hover:text-blue-400 transition"
              >
                <Home className="w-5 h-5" />
                <span>Home</span>
              </Link>
              
              <Link
                to="/search"
                className="flex items-center space-x-1 hover:text-blue-400 transition"
              >
                <Search className="w-5 h-5" />
                <span>Search</span>
              </Link>
              
              <Link
                to="/graph"
                className="flex items-center space-x-1 hover:text-blue-400 transition"
              >
                <Network className="w-5 h-5" />
                <span>Graph</span>
              </Link>
            </nav>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 container mx-auto px-4 py-8">
        {children}
      </main>

      {/* Footer */}
      <footer className="bg-gray-800 text-gray-400 py-6">
        <div className="container mx-auto px-4 text-center">
          <p className="text-sm">
            ArXiv Co-Scientist &copy; 2026 | Powered by FastAPI + React + Neo4j + ChromaDB
          </p>
          <p className="text-xs mt-2">
            Semantic Search • ML Predictions • Graph Visualization
          </p>
        </div>
      </footer>
    </div>
  );
}