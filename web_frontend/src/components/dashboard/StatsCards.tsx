import React from 'react';
import { Shield, AlertTriangle, AlertCircle, Info, TrendingUp, ArrowUp, ArrowDown } from 'lucide-react';
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
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6">
        {[...Array(5)].map((_, i) => (
          <div
            key={i}
            className="h-48 rounded-[24px] animate-pulse bg-surface border border-white/5"
          />
        ))}
      </div>
    );
  }

  const stats = [
    {
      label: 'Total Scans',
      value: totalScans,
      icon: TrendingUp,
      color: 'text-primary',
      bg: 'bg-primary/20',
      trend: '+4.5%',
      trendUp: true,
    },
    {
      label: 'Critical',
      value: critical,
      icon: Shield,
      color: 'text-accent-orange',
      bg: 'bg-accent-orange/20',
      trend: '-2.3%',
      trendUp: false,
    },
    {
      label: 'High',
      value: high,
      icon: AlertTriangle,
      color: 'text-accent-yellow',
      bg: 'bg-accent-yellow/20',
      trend: '+1.8%',
      trendUp: true,
    },
    {
      label: 'Medium',
      value: medium,
      icon: AlertCircle,
      color: 'text-accent-blue',
      bg: 'bg-accent-blue/20',
      trend: '-0.5%',
      trendUp: false,
    },
    {
      label: 'Low',
      value: low,
      icon: Info,
      color: 'text-accent-green',
      bg: 'bg-accent-green/20',
      trend: '+3.2%',
      trendUp: true,
    },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6 mb-10">
      {stats.map((stat) => {
        const Icon = stat.icon;
        const TrendIcon = stat.trendUp ? ArrowUp : ArrowDown;

        return (
          <div
            key={stat.label}
            className="group relative p-6 rounded-[24px] bg-surface border border-white/5 shadow-xl hover:shadow-2xl transition-all duration-300 hover:-translate-y-1 overflow-hidden"
          >
            {/* Background Glow Effect */}
            <div className={clsx(
              "absolute -right-6 -top-6 w-24 h-24 rounded-full blur-3xl opacity-0 group-hover:opacity-20 transition-opacity duration-500",
              stat.bg.replace('/20', '')
            )} />

            <div className="flex justify-between items-start mb-6 relative z-10">
              <span className="text-sm font-semibold text-secondary">
                {stat.label}
              </span>
              <div className={clsx(
                'w-12 h-12 rounded-full flex items-center justify-center transition-transform duration-300 group-hover:scale-110',
                stat.bg,
                stat.color
              )}>
                <Icon className="w-6 h-6" />
              </div>
            </div>

            <div className="flex flex-col gap-3 relative z-10">
              <h3 className="text-4xl font-bold text-white tracking-tight">
                {stat.value.toLocaleString()}
              </h3>
            </div>
          </div>
        );
      })}
    </div>
  );
};
