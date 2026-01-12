import { useState, useEffect, useMemo } from 'react';
import { Calendar, X } from 'lucide-react';
import { useGraphStore } from '../../hooks/useGraphStore';
import { GlassPanel } from '../shared/GlassPanel';
import { Button } from '../shared/Button';

/**
 * TimeBar - Year range filter with dual range slider
 * Allows filtering papers by publication year
 */

export function TimeBar() {
  const { allNodes, yearRange, setYearRange, graphInstance, sigmaInstance } = useGraphStore();

  // Calculate min/max years from data
  const { minYear, maxYear } = useMemo(() => {
    const years = allNodes
      .map(node => node.year)
      .filter((year): year is number => year !== undefined);
    
    if (years.length === 0) {
      return { minYear: 2000, maxYear: new Date().getFullYear() };
    }

    return {
      minYear: Math.min(...years),
      maxYear: Math.max(...years),
    };
  }, [allNodes]);

  // Local state for slider values
  const [localMin, setLocalMin] = useState(yearRange?.[0] ?? minYear);
  const [localMax, setLocalMax] = useState(yearRange?.[1] ?? maxYear);

  // Sync with store when data changes
  useEffect(() => {
    if (!yearRange) {
      setLocalMin(minYear);
      setLocalMax(maxYear);
    }
  }, [minYear, maxYear, yearRange]);

  // Count papers in range
  const papersInRange = useMemo(() => {
    return allNodes.filter(node => {
      if (!node.year) return false;
      return node.year >= localMin && node.year <= localMax;
    }).length;
  }, [allNodes, localMin, localMax]);

  /**
   * Apply year range filter
   */
  const applyFilter = () => {
    setYearRange([localMin, localMax]);
  };

  /**
   * Reset filter
   */
  const resetFilter = () => {
    setLocalMin(minYear);
    setLocalMax(maxYear);
    setYearRange(null);
  };

  /**
   * Apply filter to graph imperatively
   */
  useEffect(() => {
    if (!graphInstance || !sigmaInstance || !yearRange) return;

    allNodes.forEach(node => {
      if (!graphInstance.hasNode(node.id)) return;

      const nodeYear = node.year;
      const isInRange = nodeYear !== undefined && 
                       nodeYear >= yearRange[0] && 
                       nodeYear <= yearRange[1];

      // Update node visibility
      const currentHidden = graphInstance.getNodeAttribute(node.id, 'hidden') || false;
      
      // Only hide if not already hidden by other filters
      if (!currentHidden && !isInRange) {
        graphInstance.setNodeAttribute(node.id, 'hidden', true);
      } else if (currentHidden && isInRange) {
        // Show if in range and no other filter is hiding it
        graphInstance.setNodeAttribute(node.id, 'hidden', false);
      }
    });

    sigmaInstance.refresh();
  }, [yearRange, graphInstance, sigmaInstance, allNodes]);

  const isFiltering = yearRange !== null;
  const percentage = ((papersInRange / allNodes.length) * 100).toFixed(1);

  return (
    <GlassPanel className="fixed bottom-4 right-4 z-40 w-80">
      {/* Header */}
      <div className="flex items-center justify-between mb-4 pb-3 border-b border-slate-200 dark:border-slate-700">
        <div className="flex items-center gap-2">
          <Calendar className="w-4 h-4 text-slate-600 dark:text-slate-400" />
          <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
            Publication Year
          </h3>
        </div>
        
        {isFiltering && (
          <Button
            variant="ghost"
            size="sm"
            onClick={resetFilter}
            className="text-xs"
          >
            <X className="w-3 h-3 mr-1" />
            Reset
          </Button>
        )}
      </div>

      {/* Year Range Display */}
      <div className="mb-4 flex items-center justify-between">
        <div className="text-center flex-1">
          <div className="text-2xl font-bold text-slate-900 dark:text-slate-100">
            {localMin}
          </div>
          <div className="text-xs text-slate-500 dark:text-slate-400">
            From
          </div>
        </div>
        
        <div className="text-slate-400 dark:text-slate-600 px-2">—</div>
        
        <div className="text-center flex-1">
          <div className="text-2xl font-bold text-slate-900 dark:text-slate-100">
            {localMax}
          </div>
          <div className="text-xs text-slate-500 dark:text-slate-400">
            To
          </div>
        </div>
      </div>

      {/* Dual Range Slider */}
      <div className="mb-4 px-2">
        <div className="relative h-10">
          {/* Min slider */}
          <input
            type="range"
            min={minYear}
            max={maxYear}
            value={localMin}
            onChange={(e) => {
              const value = parseInt(e.target.value);
              if (value <= localMax) {
                setLocalMin(value);
              }
            }}
            className="absolute w-full h-2 bg-transparent appearance-none pointer-events-none z-10 [&::-webkit-slider-thumb]:pointer-events-auto [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-blue-500 [&::-webkit-slider-thumb]:cursor-pointer [&::-webkit-slider-thumb]:shadow-lg [&::-moz-range-thumb]:pointer-events-auto [&::-moz-range-thumb]:w-4 [&::-moz-range-thumb]:h-4 [&::-moz-range-thumb]:rounded-full [&::-moz-range-thumb]:bg-blue-500 [&::-moz-range-thumb]:cursor-pointer [&::-moz-range-thumb]:shadow-lg [&::-moz-range-thumb]:border-0"
          />
          
          {/* Max slider */}
          <input
            type="range"
            min={minYear}
            max={maxYear}
            value={localMax}
            onChange={(e) => {
              const value = parseInt(e.target.value);
              if (value >= localMin) {
                setLocalMax(value);
              }
            }}
            className="absolute w-full h-2 bg-transparent appearance-none pointer-events-none z-20 [&::-webkit-slider-thumb]:pointer-events-auto [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-blue-600 [&::-webkit-slider-thumb]:cursor-pointer [&::-webkit-slider-thumb]:shadow-lg [&::-moz-range-thumb]:pointer-events-auto [&::-moz-range-thumb]:w-4 [&::-moz-range-thumb]:h-4 [&::-moz-range-thumb]:rounded-full [&::-moz-range-thumb]:bg-blue-600 [&::-moz-range-thumb]:cursor-pointer [&::-moz-range-thumb]:shadow-lg [&::-moz-range-thumb]:border-0"
          />
          
          {/* Track background */}
          <div className="absolute top-1/2 -translate-y-1/2 w-full h-2 bg-slate-200 dark:bg-slate-700 rounded-full">
            {/* Active range */}
            <div
              className="absolute h-full bg-blue-500 rounded-full"
              style={{
                left: `${((localMin - minYear) / (maxYear - minYear)) * 100}%`,
                right: `${100 - ((localMax - minYear) / (maxYear - minYear)) * 100}%`,
              }}
            />
          </div>
        </div>
      </div>

      {/* Stats */}
      <div className="mb-4 p-3 bg-slate-50 dark:bg-slate-800/50 rounded-lg">
        <div className="flex items-center justify-between text-sm">
          <span className="text-slate-600 dark:text-slate-400">
            Papers in range:
          </span>
          <span className="font-bold text-slate-900 dark:text-slate-100">
            {papersInRange.toLocaleString()} ({percentage}%)
          </span>
        </div>
      </div>

      {/* Apply Button */}
      {(localMin !== (yearRange?.[0] ?? minYear) || localMax !== (yearRange?.[1] ?? maxYear)) && (
        <Button
          variant="primary"
          className="w-full"
          onClick={applyFilter}
        >
          Apply Filter
        </Button>
      )}
    </GlassPanel>
  );
}