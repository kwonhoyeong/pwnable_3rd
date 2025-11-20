import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { queryAPI, type HistoryRecord } from '../api/endpoints';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';

export const History: React.FC = () => {
  const [skip, setSkip] = useState(0);
  const limit = 10;

  const { data, isLoading } = useQuery({
    queryKey: ['history', skip, limit],
    queryFn: () => queryAPI.history(skip, limit),
    select: (res) => res.data,
  });

  const getRiskVariant = (level: string): 'critical' | 'high' | 'medium' | 'low' | 'default' => {
    switch (level.toLowerCase()) {
      case 'critical':
        return 'critical';
      case 'high':
        return 'high';
      case 'medium':
        return 'medium';
      case 'low':
        return 'low';
      default:
        return 'default';
    }
  };

  if (isLoading) return <div className="p-8">Loading...</div>;

  return (
    <div className="space-y-8">
      <h1 className="text-3xl font-bold">Analysis History</h1>

      {data?.records && data.records.length > 0 ? (
        <>
          <div className="space-y-4">
            {data.records.map((record: HistoryRecord) => (
              <Card key={record.cve_id} className="hover:shadow-md transition-shadow">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3">
                      <h3 className="text-lg font-semibold">{record.cve_id}</h3>
                      <Badge variant={getRiskVariant(record.risk_level)}>
                        {record.risk_level}
                      </Badge>
                    </div>
                    <p className="text-slate-600 mt-2">{record.analysis_summary}</p>
                  </div>
                  {record.risk_score && (
                    <div className="text-right ml-4">
                      <p className="text-2xl font-bold">{record.risk_score.toFixed(1)}</p>
                      <p className="text-sm text-slate-500">Risk Score</p>
                    </div>
                  )}
                </div>
              </Card>
            ))}
          </div>

          <div className="flex gap-4 justify-center">
            <Button
              variant="secondary"
              onClick={() => setSkip(Math.max(0, skip - limit))}
              disabled={skip === 0}
            >
              Previous
            </Button>
            <Button
              variant="secondary"
              onClick={() => setSkip(skip + limit)}
              disabled={data.records.length < limit}
            >
              Next
            </Button>
          </div>
        </>
      ) : (
        <Card>
          <p className="text-center text-slate-500">No analysis history found</p>
        </Card>
      )}
    </div>
  );
};
