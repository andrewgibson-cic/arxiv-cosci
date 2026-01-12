import { useEffect, useRef, useCallback } from 'react';
import Graph from 'graphology';
import Sigma from 'sigma';
import { useGraphStore } from '../../hooks/useGraphStore';
import { switchLayout, normalizePositions } from './Layouts';
import type { GraphNode, GraphEdge } from '../../hooks/useGraphStore';

/**
 * GraphCanvas - The core WebGL rendering component
 * Uses the "Ref Pattern" to integrate Sigma.js with React
 * This bypasses React's VDOM for performance
 */

interface GraphCanvasProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
  centerNodeId?: string | null;
  onNodeClick?: (nodeId: string) => void;
  onNodeHover?: (nodeId: string | null) => void;
  className?: string;
}

// Category to color mapping
const CATEGORY_COLORS: Record<string, string> = {
  physics: '#3B82F6',
  math: '#EF4444',
  cs: '#10B981',
  biology: '#8B5CF6',
  chemistry: '#F59E0B',
};

export function GraphCanvas({
  nodes,
  edges,
  centerNodeId,
  onNodeClick,
  onNodeHover,
  className = '',
}: GraphCanvasProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const sigmaRef = useRef<Sigma | null>(null);
  const graphRef = useRef<Graph | null>(null);
  const isInitializedRef = useRef(false);
  
  const { 
    setGraphInstance, 
    setSigmaInstance, 
    layoutMode,
    selectedNodeId,
    hoveredNodeId,
  } = useGraphStore();

  /**
   * Initialize the graph and sigma instances
   * This runs imperatively, outside React's render cycle
   */
  const initializeGraph = useCallback(() => {
    if (!containerRef.current || isInitializedRef.current) return;

    // 1. Create the Graphology data model
    const graph = new Graph();
    graphRef.current = graph;

    // Add nodes with visual attributes
    nodes.forEach((node) => {
      const isCenterNode = node.id === centerNodeId;
      const citationCount = node.citation_count || 1;
      const category = node.category || 'default';
      
      graph.addNode(node.id, {
        label: node.label,
        size: isCenterNode ? 15 : Math.log(citationCount + 1) * 3 + 5,
        color: isCenterNode ? '#3B82F6' : (CATEGORY_COLORS[category] || '#94a3b8'),
        x: 0,
        y: 0,
        // Store metadata for later use
        citation_count: node.citation_count,
        category: node.category,
        year: node.year,
      });
    });

    // Add edges
    edges.forEach((edge) => {
      if (graph.hasNode(edge.source) && graph.hasNode(edge.target)) {
        try {
          graph.addEdge(edge.source, edge.target, {
            size: edge.weight || 1,
            color: '#cbd5e1',
          });
        } catch (e) {
          // Edge might already exist, ignore
        }
      }
    });

    // Apply initial layout
    switchLayout(graph, layoutMode, centerNodeId, false);
    normalizePositions(graph);

    // 2. Create the Sigma.js renderer
    const sigma = new Sigma(graph, containerRef.current, {
      renderEdgeLabels: false,
      defaultNodeColor: '#94a3b8',
      defaultEdgeColor: '#cbd5e1',
      labelSize: 12,
      labelColor: { color: '#1f2937' },
      labelWeight: 'bold',
      enableEdgeEvents: false,
      // Performance optimizations
      minCameraRatio: 0.1,
      maxCameraRatio: 10,
    });

    sigmaRef.current = sigma;

    // 3. Register event listeners (The "Bridge" to React)
    sigma.on('clickNode', ({ node }) => {
      onNodeClick?.(node);
    });

    sigma.on('enterNode', ({ node }) => {
      onNodeHover?.(node);
    });

    sigma.on('leaveNode', () => {
      onNodeHover?.(null);
    });

    // Disable default behaviors on canvas
    sigma.on('clickStage', () => {
      onNodeClick?.(null as any); // Deselect when clicking empty space
    });

    // 4. Update global store
    setGraphInstance(graph);
    setSigmaInstance(sigma);
    
    isInitializedRef.current = true;
  }, [nodes, edges, centerNodeId, layoutMode, onNodeClick, onNodeHover, setGraphInstance, setSigmaInstance]);

  /**
   * Initialize on mount
   */
  useEffect(() => {
    initializeGraph();

    // Cleanup on unmount
    return () => {
      if (sigmaRef.current) {
        sigmaRef.current.kill();
        sigmaRef.current = null;
      }
      graphRef.current = null;
      setGraphInstance(null);
      setSigmaInstance(null);
      isInitializedRef.current = false;
    };
  }, [initializeGraph, setGraphInstance, setSigmaInstance]);

  /**
   * Update node styles when selection changes
   * This uses imperative updates, NOT React re-renders
   */
  useEffect(() => {
    const graph = graphRef.current;
    const sigma = sigmaRef.current;
    if (!graph || !sigma) return;

    graph.forEachNode((node) => {
      const isCenterNode = node === centerNodeId;
      const isSelected = node === selectedNodeId;
      const isHovered = node === hoveredNodeId;
      
      // Get original attributes
      const category = graph.getNodeAttribute(node, 'category') || 'default';
      const citationCount = graph.getNodeAttribute(node, 'citation_count') || 1;
      
      // Calculate visual state
      let color = isCenterNode ? '#3B82F6' : (CATEGORY_COLORS[category] || '#94a3b8');
      let size = isCenterNode ? 15 : Math.log(citationCount + 1) * 3 + 5;
      
      if (isSelected) {
        // Highlight selected node
        size *= 1.3;
      } else if (selectedNodeId && node !== selectedNodeId) {
        // Dim non-selected nodes when something is selected
        color = color + '40'; // Add transparency
      }
      
      if (isHovered) {
        size *= 1.2;
      }

      // Apply styles imperatively
      graph.setNodeAttribute(node, 'color', color);
      graph.setNodeAttribute(node, 'size', size);
    });

    // Trigger re-render
    sigma.refresh();
  }, [selectedNodeId, hoveredNodeId, centerNodeId]);

  /**
   * Update layout when mode changes
   */
  useEffect(() => {
    const graph = graphRef.current;
    const sigma = sigmaRef.current;
    if (!graph || !sigma) return;

    switchLayout(graph, layoutMode, centerNodeId, false);
    normalizePositions(graph);
    sigma.refresh();
  }, [layoutMode, centerNodeId]);

  return (
    <div
      ref={containerRef}
      className={`w-full h-full bg-white dark:bg-slate-900 ${className}`}
      style={{ minHeight: '600px' }}
    />
  );
}