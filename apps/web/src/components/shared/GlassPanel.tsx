import { ReactNode } from 'react';
import clsx from 'clsx';

/**
 * GlassPanel - A glassmorphism container for HUD elements
 * Provides backdrop blur and semi-transparent background
 */

interface GlassPanelProps {
  children: ReactNode;
  className?: string;
  variant?: 'light' | 'dark' | 'auto';
}

export function GlassPanel({ 
  children, 
  className = '',
  variant = 'auto'
}: GlassPanelProps) {
  return (
    <div
      className={clsx(
        'glass-panel rounded-xl p-4 smooth-transition',
        {
          'bg-white/85 dark:bg-slate-900/85': variant === 'auto',
          'bg-white/85': variant === 'light',
          'bg-slate-900/85': variant === 'dark',
        },
        className
      )}
    >
      {children}
    </div>
  );
}