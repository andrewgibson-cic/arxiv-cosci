import { useState, useEffect, useCallback, useRef } from 'react';
import { Search, Command } from 'lucide-react';
import { useGraphStore } from '../../hooks/useGraphStore';
import { GlassPanel } from '../shared/GlassPanel';
import clsx from 'clsx';

/**
 * Omnibox - Global search and navigation component
 * Supports keyboard shortcuts (Cmd+K) and "fly to" animations
 */

interface SearchResult {
  id: string;
  label: string;
  category?: string;
  citation_count?: number;
  year?: number;
}

export function Omnibox() {
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  
  const { 
    allNodes, 
    setSelectedNodeId, 
    sigmaInstance,
    setSearchQuery 
  } = useGraphStore();

  /**
   * Handle keyboard shortcuts
   */
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Cmd+K or Ctrl+K to open
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setIsOpen(true);
        setTimeout(() => inputRef.current?.focus(), 0);
      }
      
      // Escape to close
      if (e.key === 'Escape') {
        setIsOpen(false);
        setQuery('');
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  /**
   * Search logic - fuzzy match on paper titles
   */
  const performSearch = useCallback((searchQuery: string) => {
    if (!searchQuery.trim()) {
      setResults([]);
      return;
    }

    const lowerQuery = searchQuery.toLowerCase();
    const matches = allNodes
      .filter(node => 
        node.label.toLowerCase().includes(lowerQuery) ||
        node.id.toLowerCase().includes(lowerQuery)
      )
      .slice(0, 10); // Limit to 10 results

    setResults(matches);
    setSelectedIndex(0);
  }, [allNodes]);

  /**
   * Handle input change
   */
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setQuery(value);
    setSearchQuery(value);
    performSearch(value);
  };

  /**
   * Fly to selected node
   */
  const flyToNode = useCallback((nodeId: string) => {
    if (!sigmaInstance) return;

    // Get node position
    const graph = sigmaInstance.getGraph();
    if (!graph.hasNode(nodeId)) return;

    const nodeX = graph.getNodeAttribute(nodeId, 'x');
    const nodeY = graph.getNodeAttribute(nodeId, 'y');

    // Animate camera
    const camera = sigmaInstance.getCamera();
    camera.animate(
      { x: nodeX, y: nodeY, ratio: 0.3 },
      { duration: 500, easing: 'quadraticInOut' }
    );

    // Select the node
    setSelectedNodeId(nodeId);
    
    // Close omnibox
    setIsOpen(false);
    setQuery('');
  }, [sigmaInstance, setSelectedNodeId]);

  /**
   * Handle keyboard navigation in results
   */
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (results.length === 0) return;

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex(prev => Math.min(prev + 1, results.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex(prev => Math.max(prev - 1, 0));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (results[selectedIndex]) {
        flyToNode(results[selectedIndex].id);
      }
    }
  };

  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className="fixed top-4 left-1/2 -translate-x-1/2 z-50"
        aria-label="Open search (Cmd+K)"
      >
        <GlassPanel className="px-4 py-2 cursor-pointer hover:shadow-2xl">
          <div className="flex items-center gap-3 text-slate-600 dark:text-slate-400">
            <Search className="w-5 h-5" />
            <span className="text-sm">Search papers, authors, or topics...</span>
            <kbd className="inline-flex items-center border border-slate-300 dark:border-slate-600 rounded px-2 py-0.5 text-xs font-sans font-medium bg-slate-100 dark:bg-slate-800">
              <Command className="w-3 h-3 mr-1" />K
            </kbd>
          </div>
        </GlassPanel>
      </button>
    );
  }

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/20 backdrop-blur-sm z-40 animate-fade-in"
        onClick={() => setIsOpen(false)}
      />

      {/* Search Modal */}
      <div className="fixed top-4 left-1/2 -translate-x-1/2 w-full max-w-2xl z-50 px-4">
        <GlassPanel className="shadow-2xl">
          {/* Input */}
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <Search className="h-5 w-5 text-slate-400" />
            </div>
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={handleInputChange}
              onKeyDown={handleKeyDown}
              className="block w-full pl-10 pr-3 py-3 bg-transparent border-0 focus:outline-none text-slate-900 dark:text-slate-100 placeholder-slate-400 text-lg"
              placeholder="Search papers, authors, or topics..."
              autoFocus
            />
            <div className="absolute inset-y-0 right-0 pr-3 flex items-center gap-2">
              <kbd className="inline-flex items-center border border-slate-300 dark:border-slate-600 rounded px-2 py-0.5 text-xs font-sans font-medium bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400">
                ESC
              </kbd>
            </div>
          </div>

          {/* Results */}
          {results.length > 0 && (
            <div className="mt-2 border-t border-slate-200 dark:border-slate-700">
              <div className="max-h-96 overflow-y-auto custom-scrollbar py-2">
                {results.map((result, index) => (
                  <button
                    key={result.id}
                    onClick={() => flyToNode(result.id)}
                    className={clsx(
                      'w-full text-left px-3 py-2 rounded-lg smooth-transition',
                      {
                        'bg-blue-50 dark:bg-blue-900/20': index === selectedIndex,
                        'hover:bg-slate-100 dark:hover:bg-slate-800': index !== selectedIndex,
                      }
                    )}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-slate-900 dark:text-slate-100 truncate">
                          {result.label}
                        </p>
                        <p className="text-xs text-slate-500 dark:text-slate-400 font-mono mt-0.5">
                          {result.id}
                        </p>
                      </div>
                      {result.citation_count !== undefined && (
                        <span className="text-xs text-slate-500 dark:text-slate-400 whitespace-nowrap">
                          {result.citation_count} citations
                        </span>
                      )}
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* No results */}
          {query && results.length === 0 && (
            <div className="mt-2 border-t border-slate-200 dark:border-slate-700 py-4 text-center text-slate-500 dark:text-slate-400">
              No papers found
            </div>
          )}
        </GlassPanel>
      </div>
    </>
  );
}