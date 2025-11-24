import React from 'react';
import { clsx } from 'clsx';

interface BadgeProps {
  children: React.ReactNode;
  variant?: 'critical' | 'high' | 'medium' | 'low' | 'default';
  className?: string;
}

export const Badge: React.FC<BadgeProps> = ({ children, variant = 'default', className }) => {
  // Using CSS classes defined in index.css
  const variantClasses = {
    critical: 'badge-critical',
    high: 'badge-high',
    medium: 'badge-medium',
    low: 'badge-low',
    default: clsx(
      'px-3 py-1 rounded-full text-xs font-semibold',
      'border'
    ),
  };

  const defaultStyle = variant === 'default' ? {
    backgroundColor: 'var(--color-bg-tertiary)',
    color: 'var(--color-text-secondary)',
    borderColor: 'var(--color-border)',
  } : undefined;

  return (
    <span
      className={clsx('inline-flex items-center', variantClasses[variant], className)}
      style={defaultStyle}
    >
      {children}
    </span>
  );
};
