import React from 'react';
import { clsx } from 'clsx';

interface BadgeProps {
  children: React.ReactNode;
  variant?: 'critical' | 'high' | 'medium' | 'low' | 'default';
  className?: string;
}

export const Badge: React.FC<BadgeProps> = ({ children, variant = 'default', className }) => {
  const variantClasses = {
    critical: 'bg-critical-100 text-critical-800 border border-critical-300',
    high: 'bg-high-100 text-high-800 border border-high-300',
    medium: 'bg-medium-100 text-medium-800 border border-medium-300',
    low: 'bg-low-100 text-low-800 border border-low-300',
    default: 'bg-slate-100 text-slate-800 border border-slate-300',
  };

  return (
    <span className={clsx('inline-flex items-center px-3 py-1 rounded-full text-sm font-medium', variantClasses[variant], className)}>
      {children}
    </span>
  );
};
