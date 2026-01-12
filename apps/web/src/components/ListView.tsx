import { useState, useMemo } from 'react';
import { ArrowUpDown, ExternalLink } from 'lucide-react';
import { useGraphStore, useFilteredNodes } from '../hooks/useGraphStore';
import { GlassPanel } from './shared/GlassPanel';
import clsx from 'clsx';

/**
 * ListView - Accessible table view of papers
 * Provides alternative to graph visualization with sortable columns
 */

type SortField = 'label' | 'year' | 'citation_count' | 'category';
type SortOrder = 'asc' | 'desc';

export function ListView() {
  const { setSelectedNodeId } = useGraphStore();
  const filteredNodes = useFilteredNodes();
  const [sortField, setSortField] = useState<SortField>('citation_count');
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc');

  /**
   * Sort nodes based on current sort field and order
   */
  const sortedNodes = useMemo(() => {
    const sorted = [...filteredNodes].sort((a, b) => {
      let comparison = 0;

      switch (sortField) {
        case 'label':
          comparison = a.label.localeCompare(b.label);
          break;
        case 'year':
          comparison = (a.year || 0) - (b.year || 0);
          break;
        case 'citation_count':
          comparison = (a.citation_count || 0) - (b.citation_count || 0);
          break;
        case 'category':
          comparison = (a.category || '').localeCompare(b.category || '');
          break;
      }

      return sortOrder === 'asc' ? comparison : -comparison;
    });

    return sorted;
  }, [filteredNodes, sortField, sortOrder]);

  /**
   * Toggle sort for a field
   */
  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortOrder('desc');
    }
  };

  /**
   * Render sort indicator
   */
  const SortIndicator = ({ field }: { field: SortField }) => {
    if (sortField !== field) {
      return <ArrowUpDown className="w-4 h-4 opacity-30" />;
    }
    return (
      <ArrowUpDown 
        className={clsx(
          'w-4 h-4',
          sortOrder === 'desc' && 'rotate-180'
        )} 
      />
    );
  };

  return (
    <div className="h-full w-full overflow-hidden p-4">
      <GlassPanel className="h-full flex flex-col">
        {/* Header */}
        <div className="pb-4 border-b border-slate-200 dark:border-slate-700">
          <h2 className="text-2xl font-bold text-slate-900 dark:text-slate-100">
            Citation Network Papers
          </h2>
          <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">
            Showing {sortedNodes.length} papers
          </p>
        </div>

        {/* Table */}
        <div className="flex-1 overflow-auto custom-scrollbar mt-4">
          <table className="w-full text-sm">
            <thead className="sticky top-0 bg-slate-50 dark:bg-slate-800/90 backdrop-blur-sm border-b border-slate-200 dark:border-slate-700">
              <tr>
                <th className="text-left px-4 py-3">
                  <button
                    onClick={() => handleSort('label')}
                    className="flex items-center gap-2 font-semibold text-slate-700 dark:text-slate-300 hover:text-slate-900 dark:hover:text-slate-100 smooth-transition"
                  >
                    Title
                    <SortIndicator field="label" />
                  </button>
                </th>
                <th className="text-left px-4 py-3">
                  <button
                    onClick={() => handleSort('category')}
                    className="flex items-center gap-2 font-semibold text-slate-700 dark:text-slate-300 hover:text-slate-900 dark:hover:text-slate-100 smooth-transition"
                  >
                    Category
                    <SortIndicator field="category" />
                  </button>
                </th>
                <th className="text-left px-4 py-3">
                  <button
                    onClick={() => handleSort('year')}
                    className="flex items-center gap-2 font-semibold text-slate-700 dark:text-slate-300 hover:text-slate-900 dark:hover:text-slate-100 smooth-transition"
                  >
                    Year
                    <SortIndicator field="year" />
                  </button>
                </th>
                <th className="text-left px-4 py-3">
                  <button
                    onClick={() => handleSort('citation_count')}
                    className="flex items-center gap-2 font-semibold text-slate-700 dark:text-slate-300 hover:text-slate-900 dark:hover:text-slate-100 smooth-transition"
                  >
                    Citations
                    <SortIndicator field="citation_count" />
                  </button>
                </th>
                <th className="text-left px-4 py-3 w-24">
                  <span className="font-semibold text-slate-700 dark:text-slate-300">
                    Actions
                  </span>
                </th>
              </tr>
            </thead>
            <tbody>
              {sortedNodes.map((node, index) => (
                <tr
                  key={node.id}
                  className={clsx(
                    'border-b border-slate-100 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800/50 smooth-transition cursor-pointer',
                    index % 2 === 0 ? 'bg-white dark:bg-slate-900/50' : 'bg-slate-50/50 dark:bg-slate-900/30'
                  )}
                  onClick={() => setSelectedNodeId(node.id)}
                >
                  <td className="px-4 py-3">
                    <div className="flex flex-col gap-1">
                      <span className="font-medium text-slate-900 dark:text-slate-100 line-clamp-2">
                        {node.label}
                      </span>
                      <span className="text-xs text-slate-500 dark:text-slate-400 font-mono">
                        {node.id}
                      </span>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    {node.category ? (
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-300">
                        {node.category}
                      </span>
                    ) : (
                      <span className="text-slate-400 dark:text-slate-600">—</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-slate-700 dark:text-slate-300">
                      {node.year || '—'}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className="font-semibold text-slate-900 dark:text-slate-100">
                      {node.citation_count?.toLocaleString() || '0'}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <a
                      href={`https://arxiv.org/abs/${node.id}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 smooth-transition"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <ExternalLink className="w-4 h-4" />
                    </a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {/* Empty state */}
          {sortedNodes.length === 0 && (
            <div className="text-center py-12 text-slate-500 dark:text-slate-400">
              <p className="text-lg font-medium">No papers to display</p>
              <p className="text-sm mt-1">Try adjusting your filters</p>
            </div>
          )}
        </div>
      </GlassPanel>
    </div>
  );
}