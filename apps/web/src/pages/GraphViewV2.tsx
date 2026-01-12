import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useEffect } from 'react';
import { Loader2 } from 'lucide-react';
import { graphApi } from '../api/client';
import { GraphCanvas } from '../components/Graph/GraphCanvas';
import { Omnibox } from '../components/HUD/Omnibox';
import { Inspector } from '../components/HUD/Inspector';
import { Controls } from '../components/HUD/Controls';
import { useGraphStore } from '../hooks/useGraphStore';

/**
 * GraphViewV2 - The new architected graph visualization page
 * Implements the "Hybrid Architecture" with Engine (WebGL) + Shell (React)
 */

export function GraphViewV2() {
  const { arxivId } = useParams<{ arxivId?: string }>();
  const { setGraphData, setSelectedNodeId } = useGraphStore();

  // Fetch graph data from API
  const { data: network, isLoading, error } = useQuery({
    queryKey: ['graph', arxivId],
    queryFn: () => graphApi.getCitationNetwork(arxivId!, 2),
    enabled: !!arxivId,
  });

  // Update global store when data changes
  useEffect(() => {
    if (network) {
      setGraphData(
        network.nodes.map((node: any) => ({
          id: node.id,
          label: node.label,
          citation_count: node.citation_count,
          category: undefined, // API doesn't provide this yet
          year: undefined,
        })),
        network.edges,
        network.center_paper
      );
    }
  }, [network, setGraphData]);

  // Handle node interactions
  const handleNodeClick = (nodeId: string | null) => {
    setSelectedNodeId(nodeId);
  };

  const handleNodeHover = (nodeId: string | null) => {
    // Could add hover effects here
  };

  // Loading state
  if (!arxivId) {
    return (
      <div className="fixed inset-0 flex items-center justify-center bg-slate-50 dark:bg-slate-900">
        <div className="text-center max-w-md px-4">
          <h1 className="text-3xl font-bold mb-4 text-slate-900 dark:text-slate-100">
            Citation Network Visualization
          </h1>
          <p className="text-slate-600 dark:text-slate-400 mb-6">
            Enter a paper's arXiv ID to visualize its citation network
          </p>
          <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
            <p className="text-blue-800 dark:text-blue-200 text-sm">
              Interactive graph visualization powered by Sigma.js WebGL.
              Navigate to a specific paper to view its citation network.
            </p>
          </div>
        </div>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="fixed inset-0 flex items-center justify-center bg-slate-50 dark:bg-slate-900">
        <div className="text-center">
          <Loader2 className="w-12 h-12 animate-spin text-blue-600 mx-auto mb-4" />
          <p className="text-slate-600 dark:text-slate-400">
            Loading citation network...
          </p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="fixed inset-0 flex items-center justify-center bg-slate-50 dark:bg-slate-900 p-4">
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-6 max-w-md">
          <h2 className="text-lg font-bold text-red-900 dark:text-red-100 mb-2">
            Error Loading Network
          </h2>
          <p className="text-red-700 dark:text-red-300 text-sm">
            {(error as Error).message}
          </p>
        </div>
      </div>
    );
  }

  if (!network) {
    return null;
  }

  return (
    <div className="fixed inset-0 bg-slate-50 dark:bg-slate-900">
      {/* The Engine: WebGL Canvas */}
      <GraphCanvas
        nodes={network.nodes.map(node => ({
          id: node.id,
          label: node.label,
          citation_count: node.citation_count,
        }))}
        edges={network.edges}
        centerNodeId={network.center_paper}
        onNodeClick={handleNodeClick}
        onNodeHover={handleNodeHover}
        className="absolute inset-0"
      />

      {/* The Shell: HUD Components */}
      <Omnibox />
      <Inspector />
      <Controls />

      {/* Stats Overlay */}
      <div className="fixed bottom-4 left-4 z-30">
        <div className="glass-panel rounded-lg px-4 py-2">
          <div className="flex items-center gap-4 text-sm">
            <div>
              <span className="text-slate-500 dark:text-slate-400">Nodes:</span>
              <span className="ml-1 font-bold text-slate-900 dark:text-slate-100">
                {network.total_nodes}
              </span>
            </div>
            <div>
              <span className="text-slate-500 dark:text-slate-400">Edges:</span>
              <span className="ml-1 font-bold text-slate-900 dark:text-slate-100">
                {network.total_edges}
              </span>
            </div>
            <div>
              <span className="text-slate-500 dark:text-slate-400">Depth:</span>
              <span className="ml-1 font-bold text-slate-900 dark:text-slate-100">
                {network.depth}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}