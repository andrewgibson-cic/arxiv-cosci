import { useEffect } from 'react';
import { SigmaContainer, useLoadGraph, useRegisterEvents } from '@react-sigma/core';
import Graph from 'graphology';
import '@react-sigma/core/lib/react-sigma.min.css';

interface GraphNode {
  id: string;
  label: string;
  citation_count?: number;
}

interface GraphEdge {
  source: string;
  target: string;
}

interface NetworkData {
  center_node: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
  total_nodes: number;
  total_edges: number;
  depth: number;
}

interface CitationGraphProps {
  network: NetworkData;
  onNodeClick?: (nodeId: string) => void;
}

function GraphLoader({ network, onNodeClick }: CitationGraphProps) {
  const loadGraph = useLoadGraph();
  const registerEvents = useRegisterEvents();

  useEffect(() => {
    const graph = new Graph();

    // Calculate circular layout positions
    const angleStep = (2 * Math.PI) / network.nodes.length;
    const radius = 0.8;

    // Add nodes with styling
    network.nodes.forEach((node, index) => {
      const isCenterNode = node.id === network.center_node;
      const citationCount = node.citation_count || 1;
      
      // Center node in middle, others in circle
      const x = isCenterNode ? 0 : radius * Math.cos(index * angleStep);
      const y = isCenterNode ? 0 : radius * Math.sin(index * angleStep);
      
      graph.addNode(node.id, {
        label: node.label,
        size: isCenterNode ? 15 : Math.log(citationCount + 1) * 5 + 5,
        color: isCenterNode ? '#3b82f6' : '#94a3b8',
        x,
        y,
      });
    });

    // Add edges
    network.edges.forEach((edge) => {
      if (graph.hasNode(edge.source) && graph.hasNode(edge.target)) {
        graph.addEdge(edge.source, edge.target, {
          size: 1,
          color: '#cbd5e1',
        });
      }
    });

    loadGraph(graph);
  }, [network, loadGraph]);

  useEffect(() => {
    // Register click events
    registerEvents({
      clickNode: (event) => {
        if (onNodeClick) {
          onNodeClick(event.node);
        }
      },
    });
  }, [registerEvents, onNodeClick]);

  return null;
}

export function CitationGraph({ network, onNodeClick }: CitationGraphProps) {
  return (
    <div className="w-full h-[600px] border border-gray-200 rounded-lg overflow-hidden bg-white">
      <SigmaContainer
        style={{ height: '100%', width: '100%' }}
        settings={{
          renderEdgeLabels: false,
          defaultNodeColor: '#94a3b8',
          defaultEdgeColor: '#cbd5e1',
          labelSize: 12,
          labelColor: { color: '#1f2937' },
          labelWeight: 'bold',
        }}
      >
        <GraphLoader network={network} onNodeClick={onNodeClick} />
      </SigmaContainer>
    </div>
  );
}
