/**
 * TypeScript types matching the FastAPI backend schemas
 */

export interface PaperSummary {
  arxiv_id: string;
  title: string;
  abstract?: string;
  authors: string[];
  categories: string[];
  published_date?: string;
  citation_count?: number;
}

export interface PaperDetail extends PaperSummary {
  s2_id?: string;
  reference_count?: number;
  influential_citation_count?: number;
  tl_dr?: string;
  summary?: string;
  citations: PaperSummary[];
  references: PaperSummary[];
  pagerank?: number;
  betweenness?: number;
}

export interface PaperListResponse {
  papers: PaperSummary[];
  total: number;
  page: number;
  page_size: number;
  has_next: boolean;
  has_prev: boolean;
}

export interface SearchResult {
  paper: PaperSummary;
  score: number;
}

export interface SearchResponse {
  results: SearchResult[];
  query: string;
  total: number;
  search_type: 'semantic' | 'hybrid';
}

export interface SimilarPapersResponse {
  arxiv_id: string;
  similar_papers: SearchResult[];
  total: number;
}

export interface GraphNode {
  id: string;
  label: string;
  type: 'paper' | 'author' | 'concept';
  category?: string;
  citation_count?: number;
  year?: number;
}

export interface GraphEdge {
  source: string;
  target: string;
  type: 'cites' | 'authored_by' | 'uses_concept';
  weight: number;
}

export interface CitationNetworkResponse {
  center_paper: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
  depth: number;
  total_nodes: number;
  total_edges: number;
}

export interface ClusterInfo {
  cluster_id: number;
  size: number;
  papers: string[];
  label?: string;
}

export interface ClustersResponse {
  clusters: ClusterInfo[];
  total_clusters: number;
  algorithm: string;
}

export interface LinkPrediction {
  source: string;
  target: string;
  score: number;
  reason: string;
}

export interface LinkPredictionsResponse {
  predictions: LinkPrediction[];
  total: number;
}

export interface Hypothesis {
  id: string;
  title: string;
  description: string;
  confidence: number;
  papers: string[];
  gap_type: string;
}

export interface HypothesesResponse {
  hypotheses: Hypothesis[];
  total: number;
}

export interface HealthResponse {
  status: string;
  service: string;
  version: string;
}

export interface DatabaseHealthResponse {
  neo4j: {
    status: string;
    message: string;
  };
  chromadb: {
    status: string;
    message: string;
  };
}