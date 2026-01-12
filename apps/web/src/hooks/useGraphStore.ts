import { create } from 'zustand';
import type Graph from 'graphology';
import type Sigma from 'sigma';

/**
 * Graph Store - Central state management for the graph visualization
 * Uses Zustand for performance and simplicity
 */

export type LayoutMode = 'force' | 'circular';
export type ViewMode = 'graph' | 'list';

export interface GraphNode {
  id: string;
  label: string;
  citation_count?: number;
  category?: string;
  year?: number;
}

export interface GraphEdge {
  source: string;
  target: string;
  weight?: number;
}

interface GraphState {
  // Graph instances (refs, not reactive)
  graphInstance: Graph | null;
  sigmaInstance: Sigma | null;
  
  // UI State
  selectedNodeId: string | null;
  hoveredNodeId: string | null;
  searchQuery: string;
  layoutMode: LayoutMode;
  viewMode: ViewMode;
  isLayoutRunning: boolean;
  
  // Filter State
  visibleCategories: Set<string>;
  yearRange: [number, number] | null;
  
  // Data
  allNodes: GraphNode[];
  allEdges: GraphEdge[];
  centerNodeId: string | null;
  
  // Actions
  setGraphInstance: (graph: Graph | null) => void;
  setSigmaInstance: (sigma: Sigma | null) => void;
  setSelectedNodeId: (nodeId: string | null) => void;
  setHoveredNodeId: (nodeId: string | null) => void;
  setSearchQuery: (query: string) => void;
  setLayoutMode: (mode: LayoutMode) => void;
  setViewMode: (mode: ViewMode) => void;
  setIsLayoutRunning: (running: boolean) => void;
  toggleCategory: (category: string) => void;
  setYearRange: (range: [number, number] | null) => void;
  setGraphData: (nodes: GraphNode[], edges: GraphEdge[], centerNodeId: string | null) => void;
  resetFilters: () => void;
}

export const useGraphStore = create<GraphState>((set) => ({
  // Initial state
  graphInstance: null,
  sigmaInstance: null,
  selectedNodeId: null,
  hoveredNodeId: null,
  searchQuery: '',
  layoutMode: 'force',
  viewMode: 'graph',
  isLayoutRunning: false,
  visibleCategories: new Set(),
  yearRange: null,
  allNodes: [],
  allEdges: [],
  centerNodeId: null,
  
  // Actions
  setGraphInstance: (graph) => set({ graphInstance: graph }),
  
  setSigmaInstance: (sigma) => set({ sigmaInstance: sigma }),
  
  setSelectedNodeId: (nodeId) => set({ selectedNodeId: nodeId }),
  
  setHoveredNodeId: (nodeId) => set({ hoveredNodeId: nodeId }),
  
  setSearchQuery: (query) => set({ searchQuery: query }),
  
  setLayoutMode: (mode) => set({ layoutMode: mode }),
  
  setViewMode: (mode) => set({ viewMode: mode }),
  
  setIsLayoutRunning: (running) => set({ isLayoutRunning: running }),
  
  toggleCategory: (category) =>
    set((state) => {
      const newCategories = new Set(state.visibleCategories);
      if (newCategories.has(category)) {
        newCategories.delete(category);
      } else {
        newCategories.add(category);
      }
      return { visibleCategories: newCategories };
    }),
  
  setYearRange: (range) => set({ yearRange: range }),
  
  setGraphData: (nodes, edges, centerNodeId) =>
    set({
      allNodes: nodes,
      allEdges: edges,
      centerNodeId,
      // Auto-populate visible categories
      visibleCategories: new Set(
        nodes
          .map((n) => n.category)
          .filter((c): c is string => c !== undefined)
      ),
    }),
  
  resetFilters: () =>
    set((state) => ({
      visibleCategories: new Set(
        state.allNodes
          .map((n) => n.category)
          .filter((c): c is string => c !== undefined)
      ),
      yearRange: null,
      searchQuery: '',
    })),
}));

// Selectors for derived state
export const useSelectedNode = () => {
  const selectedNodeId = useGraphStore((state) => state.selectedNodeId);
  const allNodes = useGraphStore((state) => state.allNodes);
  return allNodes.find((node) => node.id === selectedNodeId);
};

export const useFilteredNodes = () => {
  const allNodes = useGraphStore((state) => state.allNodes);
  const visibleCategories = useGraphStore((state) => state.visibleCategories);
  const yearRange = useGraphStore((state) => state.yearRange);
  
  return allNodes.filter((node) => {
    // Category filter
    if (node.category && !visibleCategories.has(node.category)) {
      return false;
    }
    
    // Year filter
    if (yearRange && node.year) {
      const [minYear, maxYear] = yearRange;
      if (node.year < minYear || node.year > maxYear) {
        return false;
      }
    }
    
    return true;
  });
};