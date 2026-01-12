import { LayoutGrid, List } from 'lucide-react';
import { useGraphStore, ViewMode } from '../../hooks/useGraphStore';
import { Button } from '../shared/Button';
import clsx from 'clsx';

/**
 * ViewToggle - Switch between Graph and List views
 * Provides accessibility alternative to graph visualization
 */

export function ViewToggle() {
  const { viewMode, setViewMode } = useGraphStore();

  const toggleView = () => {
    setViewMode(viewMode === 'graph' ? 'list' : 'graph');
  };

  return (
    <div className="inline-flex rounded-lg border border-slate-300 dark:border-slate-600 bg-white/50 dark:bg-slate-800/50 p-1">
      <Button
        variant={viewMode === 'graph' ? 'primary' : 'ghost'}
        size="sm"
        onClick={() => setViewMode('graph')}
        className={clsx(
          'rounded-md px-3 py-1.5 text-xs font-medium smooth-transition',
          viewMode === 'graph' 
            ? 'bg-blue-500 text-white shadow-sm' 
            : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100'
        )}
        aria-label="Graph view"
        aria-pressed={viewMode === 'graph'}
      >
        <LayoutGrid className="w-4 h-4 mr-1.5" />
        Graph
      </Button>
      
      <Button
        variant={viewMode === 'list' ? 'primary' : 'ghost'}
        size="sm"
        onClick={() => setViewMode('list')}
        className={clsx(
          'rounded-md px-3 py-1.5 text-xs font-medium smooth-transition',
          viewMode === 'list' 
            ? 'bg-blue-500 text-white shadow-sm' 
            : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100'
        )}
        aria-label="List view"
        aria-pressed={viewMode === 'list'}
      >
        <List className="w-4 h-4 mr-1.5" />
        List
      </Button>
    </div>
  );
}