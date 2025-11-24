import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { Card } from '../ui/Card';

interface RiskDistributionChartProps {
  data?: {
    CRITICAL: number;
    HIGH: number;
    MEDIUM: number;
    LOW: number;
    Unknown: number;
  };
  isLoading?: boolean;
}

export const RiskDistributionChart: React.FC<RiskDistributionChartProps> = ({
  data,
  isLoading = false,
}) => {
  const chartData = data
    ? [
      { name: 'Critical', value: data.CRITICAL, fill: '#dc2626' },
      { name: 'High', value: data.HIGH, fill: '#f97316' },
      { name: 'Medium', value: data.MEDIUM, fill: '#3b82f6' },
      { name: 'Low', value: data.LOW, fill: '#16a34a' },
      { name: 'Unknown', value: data.Unknown, fill: '#6b7280' },
    ]
    : [];

  return (
    <Card title="위험도 분포" className="h-96">
      {isLoading ? (
        <div className="h-80 bg-slate-100 dark:bg-slate-800 rounded animate-pulse"></div>
      ) : chartData.length === 0 ? (
        <div className="h-80 flex items-center justify-center text-slate-500 dark:text-slate-400">
          No data available
        </div>
      ) : (
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} margin={{ top: 20, right: 30, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" className="dark:stroke-slate-700" />
            <XAxis dataKey="name" tick={{ fill: '#64748b' }} className="dark:fill-slate-400" />
            <YAxis tick={{ fill: '#64748b' }} className="dark:fill-slate-400" />
            <Tooltip
              contentStyle={{
                backgroundColor: '#fff',
                border: '1px solid #e2e8f0',
                borderRadius: '8px',
                color: '#1f2937',
              }}
            />
            <Bar dataKey="value" fill="#3b82f6" radius={[8, 8, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      )}
    </Card>
  );
};
