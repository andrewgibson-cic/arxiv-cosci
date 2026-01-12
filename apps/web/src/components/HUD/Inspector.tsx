import { X, ExternalLink, User, Calendar, Quote } from 'lucide-react';
import { useGraphStore, useSelectedNode } from '../../hooks/useGraphStore';
import { GlassPanel } from '../shared/GlassPanel';
import { Button } from '../shared/Button';
import { useNavigate } from 'react-router-dom';

/**
 * Inspector - Side panel showing detailed information about selected node
 * Slides in from the right when a node is selected
 */

export function Inspector() {
  const selectedNode = useSelectedNode();
  const { setSelectedNodeId, graphInstance } = useGraphStore();
  const navigate = useNavigate();

  if (!selectedNode) return null;

  const handleClose = () => {
    setSelectedNodeId(null);
  };

  const handleViewPaper = () => {
    navigate(`/paper/${selectedNode.id}`);
  };

  // Get connected nodes (citations)
  const getConnectedNodes = () => {
    if (!graphInstance) return [];
    
    try {
      const neighbors = graphInstance.neighbors(selectedNode.id);
      return neighbors.map(nodeId => ({
        id: nodeId,
        label: graphInstance.getNodeAttribute(nodeId, 'label'),
      })).slice(0, 10); // Limit to 10
    } catch {
      return [];
    }
  };

  const connectedNodes = getConnectedNodes();

  return (
    <>
      {/* Backdrop for mobile */}
      <div
        className="fixed inset-0 bg-black/20 backdrop-blur-sm z-40 lg:hidden animate-fade-in"
        onClick={handleClose}
      />

      {/* Panel */}
      <div className="fixed right-0 top-0 bottom-0 w-full sm:w-96 z-50 animate-slide-in-right">
        <GlassPanel className="h-full rounded-none sm:rounded-l-xl flex flex-col">
          {/* Header */}
          <div className="flex items-start justify-between mb-4 pb-4 border-b border-slate-200 dark:border-slate-700">
            <div className="flex-1 min-w-0">
              <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100 line-clamp-2">
                {selectedNode.label}
              </h2>
              <p className="text-xs text-slate-500 dark:text-slate-400 font-mono mt-1">
                {selectedNode.id}
              </p>
            </div>
            <button
              onClick={handleClose}
              className="flex-shrink-0 ml-2 p-1 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 smooth-transition"
              aria-label="Close inspector"
            >
              <X className="w-5 h-5 text-slate-500" />
            </button>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto custom-scrollbar space-y-4">
            {/* Metadata */}
            <div className="space-y-2">
              {selectedNode.category && (
                <div className="flex items-center gap-2 text-sm">
                  <div 
                    className="w-3 h-3 rounded-full flex-shrink-0"
                    style={{ 
                      backgroundColor: {
                        physics: '#3B82F6',
                        math: '#EF4444',
                        cs: '#10B981',
                        biology: '#8B5CF6',
                        chemistry: '#F59E0B',
                      }[selectedNode.category] || '#94a3b8'
                    }}
                  />
                  <span className="text-slate-700 dark:text-slate-300 capitalize">
                    {selectedNode.category}
                  </span>
                </div>
              )}

              {selectedNode.year && (
                <div className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-400">
                  <Calendar className="w-4 h-4 flex-shrink-0" />
                  <span>{selectedNode.year}</span>
                </div>
              )}

              {selectedNode.citation_count !== undefined && (
                <div className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-400">
                  <Quote className="w-4 h-4 flex-shrink-0" />
                  <span>{selectedNode.citation_count} citations</span>
                </div>
              )}
            </div>

            {/* Actions */}
            <div className="flex gap-2">
              <Button
                variant="primary"
                size="sm"
                icon={<ExternalLink className="w-4 h-4" />}
                onClick={handleViewPaper}
                className="flex-1"
              >
                View Full Details
              </Button>
            </div>

            {/* Connected Papers */}
            {connectedNodes.length > 0 && (
              <div>
                <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100 mb-2">
                  Connected Papers ({connectedNodes.length})
                </h3>
                <div className="space-y-1">
                  {connectedNodes.map((node) => (
                    <button
                      key={node.id}
                      onClick={() => setSelectedNodeId(node.id)}
                      className="w-full text-left p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 smooth-transition group"
                    >
                      <p className="text-sm text-slate-700 dark:text-slate-300 group-hover:text-blue-600 dark:group-hover:text-blue-400 line-clamp-2">
                        {node.label}
                      </p>
                      <p className="text-xs text-slate-500 dark:text-slate-400 font-mono mt-0.5">
                        {node.id}
                      </p>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Placeholder for future features */}
            <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-3 border border-blue-200 dark:border-blue-800">
              <p className="text-sm text-blue-900 dark:text-blue-100 font-medium mb-1">
                💡 Coming Soon
              </p>
              <p className="text-xs text-blue-700 dark:text-blue-300">
                • Abstract preview<br />
                • Author information<br />
                • "Find Gaps" analysis<br />
                • Citation strength indicators
              </p>
            </div>
          </div>
        </GlassPanel>
      </div>
    </>
  );
}