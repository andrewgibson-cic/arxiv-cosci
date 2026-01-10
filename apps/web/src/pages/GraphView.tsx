import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { graphApi } from '../api/client';
import { CitationGraph } from '../components/CitationGraph';
import { Loader2 } from 'lucide-react';

export function GraphView() {
  const { arxivId } = useParams<{ arxivId?: string }>();
  const navigate = useNavigate();

  const {  network, isLoading, error } = useQuery({
    queryKey: ['graph', arxivId],
    queryFn: () => graphApi.getCitationNetwork(arxivId!, 2),
    enabled: !!arxivId,
  });

  if (!arxivId) {
    return (
      <div className="max-w-4xl mx-auto text-center py-12">
        <h1 className="text-3xl font-bold mb-4">Citation Network Visualization</h1>
        <p className="text-gray-600 mb-6">
          Enter a paper's arXiv ID to visualize its citation network
        </p>
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <p className="text-blue-800">
            Interactive graph visualization powered by Sigma.js.
            Navigate to a specific paper to view its citation network.
          </p>
        </div>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
        <span className="ml-2 text-gray-600">Loading citation network...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <p className="text-red-800">Error loading network: {(error as Error).message}</p>
      </div>
    );
  }

  const handleNodeClick = (nodeId: string) => {
    navigate(`/paper/${nodeId}`);
  };

  return (
    <div className="max-w-7xl mx-auto">
      <div className="mb-6">
        <h1 className="text-3xl font-bold mb-2">
          Citation Network
        </h1>
        <p className="text-gray-600">
          Center: <span className="font-mono font-semibold">{arxivId}</span>
        </p>
      </div>

      {network && (
        <div className="space-y-6">
          {/* Stats */}
          <div className="bg-white rounded-lg shadow p-4 flex items-center justify-between">
            <div className="flex gap-8">
              <div>
                <p className="text-sm text-gray-500">Nodes</p>
                <p className="text-2xl font-bold text-gray-900">{network.total_nodes}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Edges</p>
                <p className="text-2xl font-bold text-gray-900">{network.total_edges}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Depth</p>
                <p className="text-2xl font-bold text-gray-900">{network.depth}</p>
              </div>
            </div>
            <p className="text-sm text-gray-500">
              Click on nodes to navigate to papers
            </p>
          </div>

          {/* Graph Visualization */}
          <div className="bg-white rounded-lg shadow-lg p-6">
            <CitationGraph network={network} onNodeClick={handleNodeClick} />
          </div>

          {/* Node List */}
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="font-bold text-lg mb-4">Papers in Network</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 max-h-96 overflow-y-auto">
              {network.nodes.map((node) => (
                <button
                  key={node.id}
                  onClick={() => handleNodeClick(node.id)}
                  className="text-left p-3 bg-gray-50 hover:bg-gray-100 rounded border border-gray-200 transition-colors"
                >
                  <p className="text-sm font-medium text-blue-600 hover:text-blue-800 truncate">
                    {node.label}
                  </p>
                  <p className="text-xs text-gray-500 font-mono">{node.id}</p>
                  {node.citation_count && (
                    <p className="text-xs text-gray-400 mt-1">
                      {node.citation_count} citations
                    </p>
                  )}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
