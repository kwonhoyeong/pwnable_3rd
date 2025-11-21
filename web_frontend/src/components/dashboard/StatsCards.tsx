import React from 'react';
import { Card } from '../ui/Card';
import { AlertTriangle, TrendingUp } from 'lucide-react';
import { clsx } from 'clsx';

interface StatsCardsProps {
  totalScans: number;
  critical: number;
  high: number;
  medium: number;
  low: number;
  isLoading?: boolean;
}

export const StatsCards: React.FC<StatsCardsProps> = ({
  totalScans,
  critical,
  high,
  medium,
  low,
  isLoading = false,
}) => {
  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
        {[...Array(5)].map((_, i) => (
          <Card key={i} className="animate-pulse">
            <div className="h-24 bg-slate-200 dark:bg-slate-700 rounded"></div>
          </Card>
        ))}
      </div>
    );
  }

  const stats = [
    {
      label: 'Total Scans',
      value: totalScans,
      icon: TrendingUp,
      color: 'text-blue-600 dark:text-blue-400',
      bgColor: 'bg-blue-50 dark:bg-blue-900/20',
    },
    {
      label: 'Critical',
      value: critical,
      icon: AlertTriangle,
      color: 'text-critical-600 dark:text-critical-400',
      bgColor: 'bg-critical-50 dark:bg-critical-900/20',
    },
    {
      label: 'High',
      value: high,
      color: 'text-high-600 dark:text-high-400',
      bgColor: 'bg-high-50 dark:bg-high-900/20',
    },
    {
      label: 'Medium',
      value: medium,
      color: 'text-medium-600 dark:text-medium-400',
      bgColor: 'bg-medium-50 dark:bg-medium-900/20',
    },
    {
      label: 'Low',
      value: low,
      color: 'text-low-600 dark:text-low-400',
      bgColor: 'bg-low-50 dark:bg-low-900/20',
    },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
      {stats.map((stat) => {
        const Icon = stat.icon;
        return (
          <Card key={stat.label} className={clsx('p-4', stat.bgColor)}>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-slate-600 dark:text-slate-400">{stat.label}</p>
                <p className="text-3xl font-bold mt-2 text-slate-900 dark:text-white">{stat.value}</p>
              </div>
              {Icon && <Icon className={clsx('w-8 h-8 opacity-20', stat.color)} />}
            </div>
          </Card>
        );
      })}
    </div>
  );
};
