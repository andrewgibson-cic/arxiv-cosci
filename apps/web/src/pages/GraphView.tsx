import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { graphApi } from '../api/client';
import { Loader2 } from 'lucide-react';

export function GraphView() {
  const { arxivId } = useParams<{ arxivId?: string }>();

  const { data: network, isLoading, error } = useQuery({
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
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <p className="text-yellow-800">
            This feature uses Sigma.js for interactive graph visualization.
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
        <p className="text-red-800">Error loading network: {error.message}</p>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto">
      <h1 className="text-3xl font-bold mb-6">
        Citation Network: {arxivId}
      </h1>

      {network && (
        <div className="bg-white rounded-lg shadow-lg p-6">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <p className="text-gray-600">
                <strong>{network.total_nodes}</strong> nodes, <strong>{network.total_edges}</strong> edges
              </p>
              <p className="text-sm text-gray-500">Depth: {network.depth}</p>
            </div>
          </div>

          {/* Placeholder for Sigma.js visualization */}
          <div className="bg-gray-100 rounded-lg p-12 text-center">
            <p className="text-gray-600 mb-4">
              📊 Interactive Graph Visualization (Sigma.js)
            </p>
            <p className="text-sm text-gray-500">
              Install dependencies with <code className="bg-gray-200 px-2 py-1 rounded">npm install</code> to enable visualization
            </p>
            
            {/* Node List */}
            <div className="mt-8 text-left">
              <h3 className="font-bold mb-3">Papers in Network:</h3>
              <div className="grid grid-cols-2 gap-2 max-h-64 overflow-y-auto">
                {network.nodes.map((node) => (
                  <div
                    key={node.id}
                    className="text-sm p-2 bg-white rounded border"
                  >
                    <a
                      href={`/paper/${node.id}`}
                      className="text-blue-600 hover:text-blue-800 font-medium"
                    >
                      {node.label}
                    </a>
                    {node.citation_count && (
                      <span className="text-gray-500 text-xs ml-2">
                        ({node.citation_count} citations)
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}