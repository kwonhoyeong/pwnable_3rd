import React from 'react';
import { clsx } from 'clsx';

interface BadgeProps {
  children: React.ReactNode;
  variant?: 'critical' | 'high' | 'medium' | 'low' | 'default';
  className?: string;
}

export const Badge: React.FC<BadgeProps> = ({ children, variant = 'default', className }) => {
  const variantClasses = {
    critical: 'bg-sentinel-error/10 text-sentinel-error border border-sentinel-error/30',
    high: 'bg-sentinel-warning/10 text-sentinel-warning border border-sentinel-warning/30',
    medium: 'bg-sentinel-primary/10 text-sentinel-primary border border-sentinel-primary/30',
    low: 'bg-sentinel-success/10 text-sentinel-success border border-sentinel-success/30',
    default: 'bg-sentinel-surface text-sentinel-text-muted border border-white/10',
  };

  return (
    <span
      className={clsx(
        'inline-flex items-center px-2.5 py-0.5 rounded text-xs font-medium',
        variantClasses[variant],
        className
      )}
    >
      {children}
    </span>
  );
};
