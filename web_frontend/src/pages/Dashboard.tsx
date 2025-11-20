import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { queryAPI } from '../api/endpoints';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';

export const Dashboard: React.FC = () => {
  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['stats'],
    queryFn: () => queryAPI.stats(),
    select: (res) => res.data,
  });

  if (statsLoading) return <div className="p-8">Loading...</div>;

  return (
    <div className="space-y-8">
      <h1 className="text-3xl font-bold">Dashboard</h1>

      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card title="Total Scans">
            <p className="text-3xl font-bold">{stats.total_scans}</p>
          </Card>
          <Card title="Critical">
            <p className="text-2xl font-bold text-critical-600">{stats.risk_distribution.CRITICAL}</p>
          </Card>
          <Card title="High">
            <p className="text-2xl font-bold text-high-600">{stats.risk_distribution.HIGH}</p>
          </Card>
          <Card title="Medium">
            <p className="text-2xl font-bold text-medium-600">{stats.risk_distribution.MEDIUM}</p>
          </Card>
        </div>
      )}
    </div>
  );
};
