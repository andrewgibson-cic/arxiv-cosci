import { useEffect } from 'react';
import { X, Filter } from 'lucide-react';
import { useGraphStore } from '../../hooks/useGraphStore';
import { GlassPanel } from '../shared/GlassPanel';
import { Button } from '../shared/Button';
import clsx from 'clsx';

/**
 * CategoryFilters - Visual filter chips for paper categories
 * Allows toggling visibility of different research categories
 */

interface CategoryInfo {
  name: string;
  color: string;
  bgColor: string;
  borderColor: string;
}

const CATEGORY_STYLES: Record<string, CategoryInfo> = {
  'Physics': {
    name: 'Physics',
    color: 'text-blue-700 dark:text-blue-300',
    bgColor: 'bg-blue-100 dark:bg-blue-900/30',
    borderColor: 'border-blue-300 dark:border-blue-700',
  },
  'Mathematics': {
    name: 'Mathematics',
    color: 'text-red-700 dark:text-red-300',
    bgColor: 'bg-red-100 dark:bg-red-900/30',
    borderColor: 'border-red-300 dark:border-red-700',
  },
  'Computer Science': {
    name: 'Computer Science',
    color: 'text-green-700 dark:text-green-300',
    bgColor: 'bg-green-100 dark:bg-green-900/30',
    borderColor: 'border-green-300 dark:border-green-700',
  },
  'Quantitative Biology': {
    name: 'Quantitative Biology',
    color: 'text-purple-700 dark:text-purple-300',
    bgColor: 'bg-purple-100 dark:bg-purple-900/30',
    borderColor: 'border-purple-300 dark:border-purple-700',
  },
  'Statistics': {
    name: 'Statistics',
    color: 'text-orange-700 dark:text-orange-300',
    bgColor: 'bg-orange-100 dark:bg-orange-900/30',
    borderColor: 'border-orange-300 dark:border-orange-700',
  },
  // Default fallback
  'default': {
    name: 'Other',
    color: 'text-slate-700 dark:text-slate-300',
    bgColor: 'bg-slate-100 dark:bg-slate-900/30',
    borderColor: 'border-slate-300 dark:border-slate-700',
  },
};

export function CategoryFilters() {
  const {
    allNodes,
    visibleCategories,
    toggleCategory,
    resetFilters,
    graphInstance,
    sigmaInstance,
  } = useGraphStore();

  // Count papers per category
  const categoryCounts = allNodes.reduce((acc, node) => {
    const category = node.category || 'Unknown';
    acc[category] = (acc[category] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  const categories = Object.keys(categoryCounts).sort();
  const totalVisible = allNodes.filter(node => 
    visibleCategories.has(node.category || '')
  ).length;

  /**
   * Apply category filters to the graph imperatively
   */
  useEffect(() => {
    if (!graphInstance || !sigmaInstance) return;

    // Update node visibility based on category filters
    allNodes.forEach(node => {
      const isVisible = visibleCategories.has(node.category || '');
      
      if (graphInstance.hasNode(node.id)) {
        // Hide filtered nodes by reducing opacity
        graphInstance.setNodeAttribute(node.id, 'hidden', !isVisible);
        
        // Also update size to indicate filtered state
        const baseSize = node.citation_count ? Math.log(node.citation_count + 1) * 2 : 5;
        graphInstance.setNodeAttribute(
          node.id, 
          'size', 
          isVisible ? baseSize : baseSize * 0.3
        );
      }
    });

    // Refresh the visualization
    sigmaInstance.refresh();
  }, [visibleCategories, graphInstance, sigmaInstance, allNodes]);

  /**
   * Get style for category
   */
  const getCategoryStyle = (category: string): CategoryInfo => {
    return CATEGORY_STYLES[category] || CATEGORY_STYLES['default'];
  };

  /**
   * Toggle all categories
   */
  const handleToggleAll = () => {
    const allVisible = categories.every(cat => visibleCategories.has(cat));
    
    if (allVisible) {
      // Hide all
      categories.forEach(cat => {
        if (visibleCategories.has(cat)) {
          toggleCategory(cat);
        }
      });
    } else {
      // Show all
      categories.forEach(cat => {
        if (!visibleCategories.has(cat)) {
          toggleCategory(cat);
        }
      });
    }
  };

  const allVisible = categories.every(cat => visibleCategories.has(cat));
  const noneVisible = categories.every(cat => !visibleCategories.has(cat));

  return (
    <GlassPanel className="fixed bottom-4 left-4 z-40 max-w-md">
      {/* Header */}
      <div className="flex items-center justify-between mb-3 pb-2 border-b border-slate-200 dark:border-slate-700">
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-slate-600 dark:text-slate-400" />
          <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
            Categories
          </h3>
          <span className="text-xs text-slate-500 dark:text-slate-400">
            ({totalVisible} / {allNodes.length})
          </span>
        </div>
        
        <div className="flex gap-1">
          <Button
            variant="ghost"
            size="sm"
            onClick={handleToggleAll}
            className="text-xs"
          >
            {allVisible ? 'Hide All' : 'Show All'}
          </Button>
          {!allVisible && (
            <Button
              variant="ghost"
              size="sm"
              onClick={resetFilters}
              className="text-xs"
            >
              Reset
            </Button>
          )}
        </div>
      </div>

      {/* Category Chips */}
      <div className="flex flex-wrap gap-2">
        {categories.map(category => {
          const style = getCategoryStyle(category);
          const isVisible = visibleCategories.has(category);
          const count = categoryCounts[category];

          return (
            <button
              key={category}
              onClick={() => toggleCategory(category)}
              className={clsx(
                'inline-flex items-center gap-2 px-3 py-1.5 rounded-full border-2 smooth-transition text-sm font-medium',
                style.color,
                isVisible ? style.bgColor : 'bg-transparent',
                style.borderColor,
                {
                  'opacity-40 hover:opacity-60': !isVisible,
                  'hover:shadow-lg': isVisible,
                }
              )}
              aria-label={`${isVisible ? 'Hide' : 'Show'} ${category}`}
            >
              <span className="truncate max-w-[150px]">
                {category}
              </span>
              
              <span className={clsx(
                'inline-flex items-center justify-center min-w-[1.5rem] h-5 px-1.5 rounded-full text-xs font-bold',
                isVisible 
                  ? 'bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300' 
                  : 'bg-slate-200 dark:bg-slate-700 text-slate-500'
              )}>
                {count}
              </span>

              {isVisible && (
                <X className="w-3 h-3" />
              )}
            </button>
          );
        })}
      </div>

      {/* Warning if nothing visible */}
      {noneVisible && (
        <div className="mt-3 pt-3 border-t border-slate-200 dark:border-slate-700 text-center">
          <p className="text-xs text-amber-600 dark:text-amber-400">
            ⚠️ No categories selected - graph is empty
          </p>
        </div>
      )}
    </GlassPanel>
  );
}