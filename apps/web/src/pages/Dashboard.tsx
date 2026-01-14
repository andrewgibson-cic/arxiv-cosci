import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { 
  Database, 
  Download, 
  Loader2, 
  Play, 
  Square, 
  Trash2,
  TrendingUp,
  FileText,
  HardDrive,
  AlertCircle,
  CheckCircle2,
  Clock,
  Activity,
  Server,
  Cpu,
  Network,
  Eye,
  Search
} from 'lucide-react';
import { ingestionApi, type IngestionConfig } from '../api/ingestion';
import { GlassPanel } from '../components/shared/GlassPanel';
import { Button } from '../components/shared/Button';
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/**
 * Dashboard - Paper Collection Management
 * Shows statistics and allows starting/stopping ingestion
 */

export function Dashboard() {
  const queryClient = useQueryClient();
  const [config, setConfig] = useState<IngestionConfig>({
    num_papers: 100,
    batch_size: 10,
    use_semantic_scholar: true,
    use_arxiv: true,
    process_pdfs: true,
  });

  // Fetch stats
  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['ingestion-stats'],
    queryFn: () => ingestionApi.getStats(),
    refetchInterval: 5000,
  });

  // Fetch status
  const { data: status } = useQuery({
    queryKey: ['ingestion-status'],
    queryFn: () => ingestionApi.getStatus(),
    refetchInterval: 1000,
  });

  // Mutations
  const startMutation = useMutation({
    mutationFn: (config: IngestionConfig) => ingestionApi.startIngestion(config),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ingestion-status'] });
    },
  });

  const stopMutation = useMutation({
    mutationFn: () => ingestionApi.stopIngestion(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ingestion-status'] });
    },
  });

  const clearMutation = useMutation({
    mutationFn: () => ingestionApi.clearData(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ingestion-stats'] });
    },
  });

  const handleStart = () => {
    if (confirm(`Start ingesting ${config.num_papers} papers?`)) {
      startMutation.mutate(config);
    }
  };

  const handleStop = () => {
    if (confirm('Stop the ingestion process?')) {
      stopMutation.mutate();
    }
  };

  const handleClear = () => {
    if (confirm('⚠️ WARNING: This will delete all collected papers. Are you sure?')) {
      if (confirm('This action cannot be undone. Proceed?')) {
        clearMutation.mutate();
      }
    }
  };

  const navigate = useNavigate();
  
  // Fetch system health
  const { data: systemHealth } = useQuery({
    queryKey: ['system-health'],
    queryFn: async () => {
      const response = await axios.get(`${API_BASE_URL}/api/system/health`);
      return response.data;
    },
    refetchInterval: 10000, // Every 10 seconds
  });

  const isRunning = status?.is_running || false;

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900 p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex justify-between items-start">
          <div>
            <h1 className="text-3xl font-bold text-slate-900 dark:text-slate-100 flex items-center gap-3">
              <Database className="w-8 h-8" />
              Paper Collection Dashboard
            </h1>
            <p className="text-slate-600 dark:text-slate-400 mt-1">
              Manage and monitor your scientific paper database
            </p>
          </div>
          
          {/* Quick Navigation */}
          <div className="flex gap-2">
            <Button
              variant="ghost"
              onClick={() => navigate('/graph')}
              className="flex items-center gap-2"
            >
              <Network className="w-4 h-4" />
              View Graph
            </Button>
            <Button
              variant="ghost"
              onClick={() => navigate('/search')}
              className="flex items-center gap-2"
            >
              <Search className="w-4 h-4" />
              Search
            </Button>
          </div>
        </div>

        {/* System Health */}
        {systemHealth && (
          <GlassPanel>
            <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-4 flex items-center gap-2">
              <Activity className="w-5 h-5" />
              System Health
              <span className={`ml-auto text-sm px-3 py-1 rounded-full ${
                systemHealth.status === 'healthy' ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' :
                systemHealth.status === 'degraded' ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400' :
                'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
              }`}>
                {systemHealth.status.toUpperCase()}
              </span>
            </h2>
            
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {systemHealth.services?.map((service: any) => (
                <div key={service.name} className="flex items-center gap-3 p-3 rounded-lg bg-slate-50 dark:bg-slate-800">
                  {service.status === 'running' ? (
                    <CheckCircle2 className="w-5 h-5 text-green-500 flex-shrink-0" />
                  ) : (
                    <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0" />
                  )}
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-slate-900 dark:text-slate-100 truncate">
                      {service.name}
                    </p>
                    <p className="text-xs text-slate-500 dark:text-slate-400 truncate">
                      {service.details || service.status}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </GlassPanel>
        )}

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <GlassPanel>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-600 dark:text-slate-400">Total Papers</p>
                <p className="text-3xl font-bold text-slate-900 dark:text-slate-100 mt-1">
                  {statsLoading ? '...' : stats?.total_papers.toLocaleString()}
                </p>
              </div>
              <FileText className="w-10 h-10 text-blue-500 opacity-50" />
            </div>
          </GlassPanel>

          <GlassPanel>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-600 dark:text-slate-400">Processed</p>
                <p className="text-3xl font-bold text-green-600 dark:text-green-400 mt-1">
                  {statsLoading ? '...' : stats?.processed_papers.toLocaleString()}
                </p>
              </div>
              <CheckCircle2 className="w-10 h-10 text-green-500 opacity-50" />
            </div>
          </GlassPanel>

          <GlassPanel>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-600 dark:text-slate-400">Pending</p>
                <p className="text-3xl font-bold text-orange-600 dark:text-orange-400 mt-1">
                  {statsLoading ? '...' : stats?.unprocessed_papers.toLocaleString()}
                </p>
              </div>
              <Clock className="w-10 h-10 text-orange-500 opacity-50" />
            </div>
          </GlassPanel>

          <GlassPanel>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-600 dark:text-slate-400">Storage Used</p>
                <p className="text-3xl font-bold text-purple-600 dark:text-purple-400 mt-1">
                  {statsLoading ? '...' : `${stats?.total_size_mb} MB`}
                </p>
              </div>
              <HardDrive className="w-10 h-10 text-purple-500 opacity-50" />
            </div>
          </GlassPanel>
        </div>

        {/* Categories */}
        {stats && stats.categories && Object.keys(stats.categories).length > 0 && (
          <GlassPanel>
            <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-4 flex items-center gap-2">
              <TrendingUp className="w-5 h-5" />
              Papers by Category
            </h2>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
              {Object.entries(stats.categories).map(([category, count]) => (
                <div key={category} className="text-center">
                  <p className="text-2xl font-bold text-slate-900 dark:text-slate-100">
                    {count}
                  </p>
                  <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">
                    {category}
                  </p>
                </div>
              ))}
            </div>
          </GlassPanel>
        )}

        {/* Ingestion Control */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Configuration */}
          <GlassPanel>
            <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-4 flex items-center gap-2">
              <Download className="w-5 h-5" />
              Ingestion Configuration
            </h2>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                  Number of Papers
                </label>
                <input
                  type="number"
                  value={config.num_papers}
                  onChange={(e) => setConfig({ ...config, num_papers: parseInt(e.target.value) })}
                  disabled={isRunning}
                  className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
                  min="10"
                  max="1000"
                  step="10"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                  Batch Size
                </label>
                <input
                  type="number"
                  value={config.batch_size}
                  onChange={(e) => setConfig({ ...config, batch_size: parseInt(e.target.value) })}
                  disabled={isRunning}
                  className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
                  min="5"
                  max="50"
                  step="5"
                />
              </div>

              <div className="flex gap-2 pt-4">
                {!isRunning ? (
                  <Button
                    variant="primary"
                    onClick={handleStart}
                    disabled={startMutation.isPending}
                    className="flex-1"
                  >
                    <Play className="w-4 h-4 mr-2" />
                    Start Ingestion
                  </Button>
                ) : (
                  <Button
                    variant="secondary"
                    onClick={handleStop}
                    disabled={stopMutation.isPending}
                    className="flex-1"
                  >
                    <Square className="w-4 h-4 mr-2" />
                    Stop
                  </Button>
                )}

                <Button
                  variant="ghost"
                  onClick={handleClear}
                  disabled={isRunning || clearMutation.isPending}
                  className="text-red-600 hover:text-red-700"
                >
                  <Trash2 className="w-4 h-4" />
                </Button>
              </div>
            </div>
          </GlassPanel>

          {/* Status */}
          <GlassPanel>
            <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-4">
              Ingestion Status
            </h2>

            {status?.is_running ? (
              <div className="space-y-4">
                <div className="flex items-center gap-3">
                  <Loader2 className="w-5 h-5 animate-spin text-blue-500" />
                  <span className="text-sm text-slate-700 dark:text-slate-300">
                    {status.current_status}
                  </span>
                </div>

                <div>
                  <div className="flex justify-between text-sm text-slate-600 dark:text-slate-400 mb-2">
                    <span>Progress</span>
                    <span>{status.progress_percentage.toFixed(1)}%</span>
                  </div>
                  <div className="w-full h-3 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-blue-500 to-purple-500 smooth-transition"
                      style={{ width: `${status.progress_percentage}%` }}
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4 pt-2">
                  <div>
                    <p className="text-sm text-slate-600 dark:text-slate-400">Batch</p>
                    <p className="text-xl font-bold text-slate-900 dark:text-slate-100">
                      {status.current_batch} / {status.total_batches}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-slate-600 dark:text-slate-400">Processed</p>
                    <p className="text-xl font-bold text-slate-900 dark:text-slate-100">
                      {status.papers_processed}
                    </p>
                  </div>
                </div>

                {status.error && (
                  <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg flex items-start gap-2">
                    <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
                    <p className="text-sm text-red-700 dark:text-red-300">{status.error}</p>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center py-8 text-slate-500 dark:text-slate-400">
                <Clock className="w-12 h-12 mx-auto mb-3 opacity-50" />
                <p>{status?.current_status || 'No ingestion process running'}</p>
              </div>
            )}
          </GlassPanel>
        </div>
      </div>
    </div>
  );
}
