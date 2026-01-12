import Graph from 'graphology';
import forceAtlas2 from 'graphology-layout-forceatlas2';
import circular from 'graphology-layout/circular';
import type { LayoutMode } from '../../hooks/useGraphStore';

/**
 * Layout Engine - Manages graph layout algorithms
 * Supports ForceAtlas2 (force-directed) and Circular layouts
 */

export interface LayoutSettings {
  iterations?: number;
  settings?: {
    gravity?: number;
    scalingRatio?: number;
    strongGravityMode?: boolean;
    barnesHutOptimize?: boolean;
    barnesHutTheta?: number;
    slowDown?: number;
  };
}

/**
 * Apply circular layout to graph
 * Places nodes in a circle around the center
 */
export function applyCircularLayout(
  graph: Graph,
  centerNodeId?: string | null
): void {
  if (graph.order === 0) return;

  const nodes = graph.nodes();
  
  if (centerNodeId && graph.hasNode(centerNodeId)) {
    // Place center node at origin
    graph.setNodeAttribute(centerNodeId, 'x', 0);
    graph.setNodeAttribute(centerNodeId, 'y', 0);
    
    // Place other nodes in circle
    const otherNodes = nodes.filter(n => n !== centerNodeId);
    const angleStep = (2 * Math.PI) / otherNodes.length;
    const radius = 0.8;
    
    otherNodes.forEach((node, index) => {
      const angle = index * angleStep;
      graph.setNodeAttribute(node, 'x', radius * Math.cos(angle));
      graph.setNodeAttribute(node, 'y', radius * Math.sin(angle));
    });
  } else {
    // Standard circular layout for all nodes
    circular.assign(graph, { scale: 0.8 });
  }
}

/**
 * Apply ForceAtlas2 layout to graph
 * Physics-based layout that shows natural clustering
 */
export function applyForceAtlas2Layout(
  graph: Graph,
  settings?: LayoutSettings
): void {
  if (graph.order === 0) return;

  const defaultSettings = {
    iterations: settings?.iterations || 500,
    settings: {
      gravity: settings?.settings?.gravity || 1,
      scalingRatio: settings?.settings?.scalingRatio || 10,
      strongGravityMode: settings?.settings?.strongGravityMode || false,
      barnesHutOptimize: settings?.settings?.barnesHutOptimize || true,
      barnesHutTheta: settings?.settings?.barnesHutTheta || 0.5,
      slowDown: settings?.settings?.slowDown || 1,
      ...settings?.settings,
    },
  };

  // Run layout synchronously
  forceAtlas2.assign(graph, defaultSettings);
}

/**
 * Start animated ForceAtlas2 layout
 * Returns a cancel function to stop the animation
 */
export function startAnimatedLayout(
  graph: Graph,
  onIteration?: (iteration: number) => void,
  maxIterations: number = 500
): () => void {
  let iteration = 0;
  let cancelled = false;

  const settings = {
    gravity: 1,
    scalingRatio: 10,
    strongGravityMode: false,
    barnesHutOptimize: true,
    barnesHutTheta: 0.5,
    slowDown: 1,
  };

  // Initialize positions if not set
  graph.forEachNode((node) => {
    if (!graph.getNodeAttribute(node, 'x')) {
      graph.setNodeAttribute(node, 'x', Math.random() - 0.5);
    }
    if (!graph.getNodeAttribute(node, 'y')) {
      graph.setNodeAttribute(node, 'y', Math.random() - 0.5);
    }
  });

  function iterate() {
    if (cancelled || iteration >= maxIterations) {
      return;
    }

    // Run one iteration
    forceAtlas2.assign(graph, { iterations: 1, settings });
    iteration++;
    
    onIteration?.(iteration);

    // Schedule next iteration
    requestAnimationFrame(iterate);
  }

  // Start animation
  requestAnimationFrame(iterate);

  // Return cancel function
  return () => {
    cancelled = true;
  };
}

/**
 * Switch between layout modes
 */
export function switchLayout(
  graph: Graph,
  mode: LayoutMode,
  centerNodeId?: string | null,
  animated: boolean = false
): (() => void) | void {
  if (mode === 'circular') {
    applyCircularLayout(graph, centerNodeId);
  } else if (mode === 'force') {
    if (animated) {
      return startAnimatedLayout(graph);
    } else {
      applyForceAtlas2Layout(graph);
    }
  }
}

/**
 * Initialize random positions for nodes
 * Used before running force-directed layout
 */
export function initializeRandomPositions(graph: Graph): void {
  graph.forEachNode((node) => {
    graph.setNodeAttribute(node, 'x', Math.random() - 0.5);
    graph.setNodeAttribute(node, 'y', Math.random() - 0.5);
  });
}

/**
 * Center and scale graph to fit viewport
 */
export function normalizePositions(graph: Graph, targetSize: number = 1): void {
  if (graph.order === 0) return;

  // Find bounds
  let minX = Infinity, maxX = -Infinity;
  let minY = Infinity, maxY = -Infinity;

  graph.forEachNode((node) => {
    const x = graph.getNodeAttribute(node, 'x');
    const y = graph.getNodeAttribute(node, 'y');
    minX = Math.min(minX, x);
    maxX = Math.max(maxX, x);
    minY = Math.min(minY, y);
    maxY = Math.max(maxY, y);
  });

  const width = maxX - minX;
  const height = maxY - minY;
  const scale = targetSize / Math.max(width, height);

  // Center and scale
  const centerX = (minX + maxX) / 2;
  const centerY = (minY + maxY) / 2;

  graph.forEachNode((node) => {
    const x = graph.getNodeAttribute(node, 'x');
    const y = graph.getNodeAttribute(node, 'y');
    graph.setNodeAttribute(node, 'x', (x - centerX) * scale);
    graph.setNodeAttribute(node, 'y', (y - centerY) * scale);
  });
}