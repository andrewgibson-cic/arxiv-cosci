import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, TrendingUp, Network, Sparkles } from 'lucide-react';

export function Home() {
  const [query, setQuery] = useState('');
  const navigate = useNavigate();

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      navigate(`/search?q=${encodeURIComponent(query)}`);
    }
  };

  return (
    <div className="max-w-4xl mx-auto">
      {/* Hero Section */}
      <div className="text-center py-16">
        <h1 className="text-5xl font-bold mb-4">
          Discover Scientific Knowledge
        </h1>
        <p className="text-xl text-gray-600 mb-8">
          Semantic search, citation networks, and ML-powered insights for physics and mathematics research
        </p>

        {/* Search Box */}
        <form onSubmit={handleSearch} className="max-w-2xl mx-auto">
          <div className="relative">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search for papers, concepts, or authors..."
              className="w-full px-6 py-4 text-lg border-2 border-gray-300 rounded-lg focus:border-blue-500 focus:outline-none"
            />
            <button
              type="submit"
              className="absolute right-2 top-2 px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition flex items-center space-x-2"
            >
              <Search className="w-5 h-5" />
              <span>Search</span>
            </button>
          </div>
        </form>

        <p className="text-sm text-gray-500 mt-4">
          Try searching for "quantum error correction", "topological phases", or any physics/math topic
        </p>
      </div>

      {/* Features Grid */}
      <div className="grid md:grid-cols-3 gap-8 mt-16">
        <div className="p-6 bg-white rounded-lg shadow-md hover:shadow-lg transition">
          <div className="flex items-center space-x-3 mb-4">
            <Search className="w-8 h-8 text-blue-600" />
            <h3 className="text-xl font-bold">Semantic Search</h3>
          </div>
          <p className="text-gray-600">
            Find papers by meaning, not just keywords. Powered by sentence transformers and vector search.
          </p>
        </div>

        <div className="p-6 bg-white rounded-lg shadow-md hover:shadow-lg transition">
          <div className="flex items-center space-x-3 mb-4">
            <Network className="w-8 h-8 text-green-600" />
            <h3 className="text-xl font-bold">Citation Networks</h3>
          </div>
          <p className="text-gray-600">
            Visualize how papers connect through citations. Discover research communities and influential work.
          </p>
        </div>

        <div className="p-6 bg-white rounded-lg shadow-md hover:shadow-lg transition">
          <div className="flex items-center space-x-3 mb-4">
            <Sparkles className="w-8 h-8 text-purple-600" />
            <h3 className="text-xl font-bold">ML Predictions</h3>
          </div>
          <p className="text-gray-600">
            GraphSAGE link prediction finds missing citations. LLM-generated hypotheses reveal research gaps.
          </p>
        </div>
      </div>

      {/* Stats Section */}
      <div className="mt-16 p-8 bg-gray-100 rounded-lg">
        <h2 className="text-2xl font-bold text-center mb-8">Platform Features</h2>
        <div className="grid md:grid-cols-4 gap-6 text-center">
          <div>
            <div className="text-3xl font-bold text-blue-600">100k+</div>
            <div className="text-gray-600 mt-2">Research Papers</div>
          </div>
          <div>
            <div className="text-3xl font-bold text-green-600">Fast</div>
            <div className="text-gray-600 mt-2">Semantic Search</div>
          </div>
          <div>
            <div className="text-3xl font-bold text-purple-600">AI</div>
            <div className="text-gray-600 mt-2">Powered Analysis</div>
          </div>
          <div>
            <div className="text-3xl font-bold text-orange-600">$0</div>
            <div className="text-gray-600 mt-2">Free & Open Source</div>
          </div>
        </div>
      </div>

      {/* Tech Stack */}
      <div className="mt-12 text-center text-sm text-gray-500">
        <p>Built with FastAPI • React • Neo4j • ChromaDB • Gemini AI • GraphSAGE</p>
      </div>
    </div>
  );
}