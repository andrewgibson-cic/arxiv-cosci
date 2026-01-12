import { ZoomIn, ZoomOut, Maximize2, GitBranch, Circle } from 'lucide-react';
import { useGraphStore } from '../../hooks/useGraphStore';
import { GlassPanel } from '../shared/GlassPanel';
import { Button } from '../shared/Button';
import clsx from 'clsx';

/**
 * Controls - Graph manipulation controls (zoom, layout, reset)
 * Positioned in the bottom-right corner
 */

export function Controls() {
  const { 
    sigmaInstance, 
    layoutMode, 
    setLayoutMode, 
    isLayoutRunning 
  } = useGraphStore();

  const handleZoomIn = () => {
    if (!sigmaInstance) return;
    const camera = sigmaInstance.getCamera();
    camera.animatedZoom({ duration: 300 });
  };

  const handleZoomOut = () => {
    if (!sigmaInstance) return;
    const camera = sigmaInstance.getCamera();
    camera.animatedUnzoom({ duration: 300 });
  };

  const handleResetView = () => {
    if (!sigmaInstance) return;
    const camera = sigmaInstance.getCamera();
    camera.animate(
      { x: 0.5, y: 0.5, ratio: 1 },
      { duration: 500, easing: 'quadraticInOut' }
    );
  };

  const handleLayoutToggle = () => {
    const newMode = layoutMode === 'force' ? 'circular' : 'force';
    setLayoutMode(newMode);
  };

  return (
    <div className="fixed bottom-4 right-4 z-30">
      <GlassPanel className="p-2">
        <div className="flex flex-col gap-2">
          {/* Zoom Controls */}
          <div className="flex gap-2">
            <button
              onClick={handleZoomIn}
              className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 smooth-transition"
              aria-label="Zoom in"
              title="Zoom in"
            >
              <ZoomIn className="w-5 h-5 text-slate-700 dark:text-slate-300" />
            </button>
            <button
              onClick={handleZoomOut}
              className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 smooth-transition"
              aria-label="Zoom out"
              title="Zoom out"
            >
              <ZoomOut className="w-5 h-5 text-slate-700 dark:text-slate-300" />
            </button>
          </div>

          {/* Divider */}
          <div className="h-px bg-slate-200 dark:bg-slate-700" />

          {/* Layout Toggle */}
          <button
            onClick={handleLayoutToggle}
            disabled={isLayoutRunning}
            className={clsx(
              'p-2 rounded-lg smooth-transition',
              {
                'hover:bg-slate-100 dark:hover:bg-slate-800': !isLayoutRunning,
                'opacity-50 cursor-not-allowed': isLayoutRunning,
              }
            )}
            aria-label={`Switch to ${layoutMode === 'force' ? 'circular' : 'force-directed'} layout`}
            title={`Switch to ${layoutMode === 'force' ? 'circular' : 'force-directed'} layout`}
          >
            {layoutMode === 'force' ? (
              <Circle className="w-5 h-5 text-slate-700 dark:text-slate-300" />
            ) : (
              <GitBranch className="w-5 h-5 text-slate-700 dark:text-slate-300" />
            )}
          </button>

          {/* Reset View */}
          <button
            onClick={handleResetView}
            className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 smooth-transition"
            aria-label="Reset view"
            title="Reset view"
          >
            <Maximize2 className="w-5 h-5 text-slate-700 dark:text-slate-300" />
          </button>
        </div>
      </GlassPanel>
    </div>
  );
}