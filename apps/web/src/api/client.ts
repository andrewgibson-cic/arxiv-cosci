/**
 * API client for ArXiv Co-Scientist backend
 * Uses Axios for HTTP requests with TypeScript types
 */
import axios from 'axios';
import type {
  PaperListResponse,
  PaperDetail,
  SearchResponse,
  SimilarPapersResponse,
  CitationNetworkResponse,
  ClustersResponse,
  LinkPredictionsResponse,
  HypothesesResponse,
  HealthResponse,
  DatabaseHealthResponse,
} from '../types/api';

// Create axios instance with base configuration
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for debugging
api.interceptors.request.use(
  (config) => {
    console.log(`[API] ${config.method?.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => {
    console.error('[API] Request error:', error);
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      // Server responded with error status
      console.error('[API] Response error:', error.response.status, error.response.data);
    } else if (error.request) {
      // Request made but no response
      console.error('[API] No response received:', error.request);
    } else {
      // Error in request setup
      console.error('[API] Request setup error:', error.message);
    }
    return Promise.reject(error);
  }
);

/**
 * Health API
 */
export const healthApi = {
  getHealth: async (): Promise<HealthResponse> => {
    const { data } = await api.get('/health');
    return data;
  },

  getDatabaseHealth: async (): Promise<DatabaseHealthResponse> => {
    const { data } = await api.get('/health/db');
    return data;
  },
};

/**
 * Papers API
 */
export const papersApi = {
  list: async (params?: {
    page?: number;
    page_size?: number;
    category?: string;
  }): Promise<PaperListResponse> => {
    const { data } = await api.get('/papers', { params });
    return data;
  },

  get: async (
    arxivId: string,
    params?: {
      include_citations?: boolean;
      include_references?: boolean;
    }
  ): Promise<PaperDetail> => {
    const { data } = await api.get(`/papers/${arxivId}`, { params });
    return data;
  },

  batch: async (arxivIds: string[]): Promise<{ papers: PaperDetail[]; found: number; not_found: string[] }> => {
    const { data } = await api.post('/papers/batch', { arxiv_ids: arxivIds });
    return data;
  },
};

/**
 * Search API
 */
export const searchApi = {
  semantic: async (query: string, limit: number = 10): Promise<SearchResponse> => {
    const { data } = await api.get('/search/semantic', {
      params: { q: query, limit },
    });
    return data;
  },

  hybrid: async (query: string, limit: number = 10): Promise<SearchResponse> => {
    const { data } = await api.get('/search/hybrid', {
      params: { q: query, limit },
    });
    return data;
  },

  similar: async (arxivId: string, limit: number = 10): Promise<SimilarPapersResponse> => {
    const { data } = await api.get(`/search/similar/${arxivId}`, {
      params: { limit },
    });
    return data;
  },
};

/**
 * Graph API
 */
export const graphApi = {
  getCitationNetwork: async (
    arxivId: string,
    depth: number = 2
  ): Promise<CitationNetworkResponse> => {
    const { data } = await api.get(`/graph/citations/${arxivId}`, {
      params: { depth },
    });
    return data;
  },

  getClusters: async (minSize: number = 5): Promise<ClustersResponse> => {
    const { data } = await api.get('/graph/clusters', {
      params: { min_size: minSize },
    });
    return data;
  },
};

/**
 * Predictions API
 */
export const predictionsApi = {
  getLinks: async (limit: number = 10): Promise<LinkPredictionsResponse> => {
    const { data} = await api.get('/predictions/links', {
      params: { limit },
    });
    return data;
  },

  getHypotheses: async (limit: number = 10): Promise<HypothesesResponse> => {
    const { data } = await api.get('/predictions/hypotheses', {
      params: { limit },
    });
    return data;
  },
};

// Export default api instance for custom requests
export default api;