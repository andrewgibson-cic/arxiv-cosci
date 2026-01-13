/**
 * Ingestion API Client
 * Handles paper collection and processing operations
 */

import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

export interface IngestionStats {
  total_papers: number;
  processed_papers: number;
  unprocessed_papers: number;
  total_size_mb: number;
  categories: Record<string, number>;
  last_updated: string | null;
}

export interface IngestionStatus {
  is_running: boolean;
  current_batch: number;
  total_batches: number;
  papers_processed: number;
  papers_failed: number;
  started_at: string | null;
  estimated_completion: string | null;
  current_status: string;
  error: string | null;
  progress_percentage: number;
}

export interface IngestionConfig {
  num_papers: number;
  batch_size: number;
  use_semantic_scholar: boolean;
  use_arxiv: boolean;
  process_pdfs: boolean;
}

export const ingestionApi = {
  /**
   * Get statistics about collected papers
   */
  async getStats(): Promise<IngestionStats> {
    const response = await axios.get(`${API_BASE_URL}/ingestion/stats`);
    return response.data;
  },

  /**
   * Get current ingestion process status
   */
  async getStatus(): Promise<IngestionStatus> {
    const response = await axios.get(`${API_BASE_URL}/ingestion/status`);
    return response.data;
  },

  /**
   * Start paper ingestion process
   */
  async startIngestion(config: IngestionConfig): Promise<{ message: string; config: IngestionConfig }> {
    const response = await axios.post(`${API_BASE_URL}/ingestion/start`, config);
    return response.data;
  },

  /**
   * Stop running ingestion process
   */
  async stopIngestion(): Promise<{ message: string }> {
    const response = await axios.post(`${API_BASE_URL}/ingestion/stop`);
    return response.data;
  },

  /**
   * Clear all collected data (USE WITH CAUTION)
   */
  async clearData(): Promise<{ message: string; files_deleted: number }> {
    const response = await axios.delete(`${API_BASE_URL}/ingestion/clear`);
    return response.data;
  },
};