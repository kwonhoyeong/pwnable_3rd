import React from 'react';
import { Link } from 'react-router-dom';
import { Card } from '../ui/Card';
import { Badge } from '../ui/Badge';
import { ChevronRight } from 'lucide-react';
import { clsx } from 'clsx';

export interface ScanRecord {
  cve_id: string;
  risk_level: string;
  risk_score?: number;
  analysis_summary: string;
  created_at?: string;
}

interface RecentScansTableProps {
  data?: ScanRecord[];
  isLoading?: boolean;
}

export const RecentScansTable: React.FC<RecentScansTableProps> = ({
  data = [],
  isLoading = false,
}) => {
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

  const formatDate = (dateString?: string) => {
    if (!dateString) return 'N/A';
    try {
      return new Date(dateString).toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
      });
    } catch {
      return 'Invalid date';
    }
  };

  return (
    <Card title="Recent Scans" className="overflow-hidden">
      {isLoading ? (
        <div className="space-y-3">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-16 bg-slate-100 dark:bg-slate-800 rounded animate-pulse"></div>
          ))}
        </div>
      ) : data.length === 0 ? (
        <div className="text-center py-8 text-slate-500 dark:text-slate-400">
          No recent scans found
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className={clsx(
              'bg-slate-50 dark:bg-slate-800',
              'border-b border-slate-200 dark:border-slate-700'
            )}>
              <tr>
                <th className="px-4 py-3 text-left text-sm font-semibold text-slate-700 dark:text-slate-300">CVE ID</th>
                <th className="px-4 py-3 text-left text-sm font-semibold text-slate-700 dark:text-slate-300">Risk Level</th>
                <th className="px-4 py-3 text-left text-sm font-semibold text-slate-700 dark:text-slate-300">Score</th>
                <th className="px-4 py-3 text-left text-sm font-semibold text-slate-700 dark:text-slate-300">Summary</th>
                <th className="px-4 py-3 text-left text-sm font-semibold text-slate-700 dark:text-slate-300">Date</th>
                <th className="px-4 py-3 text-center text-sm font-semibold text-slate-700 dark:text-slate-300">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 dark:divide-slate-700">
              {data.map((scan) => (
                <tr
                  key={scan.cve_id}
                  className={clsx(
                    'hover:bg-slate-50 dark:hover:bg-slate-800/50',
                    'border-b border-slate-200 dark:border-slate-700',
                    'transition-colors'
                  )}
                >
                  <td className="px-4 py-3 text-sm font-medium text-slate-900 dark:text-white">
                    {scan.cve_id}
                  </td>
                  <td className="px-4 py-3">
                    <Badge variant={getRiskVariant(scan.risk_level)}>
                      {scan.risk_level}
                    </Badge>
                  </td>
                  <td className="px-4 py-3 text-sm font-semibold text-slate-900 dark:text-white">
                    {scan.risk_score ? scan.risk_score.toFixed(1) : 'N/A'}
                  </td>
                  <td className="px-4 py-3 text-sm text-slate-600 dark:text-slate-400 max-w-xs truncate">
                    {scan.analysis_summary}
                  </td>
                  <td className="px-4 py-3 text-sm text-slate-500 dark:text-slate-500">
                    {formatDate(scan.created_at)}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <Link
                      to={`/report/${scan.cve_id}`}
                      className={clsx(
                        'inline-flex items-center justify-center p-2',
                        'hover:bg-slate-200 dark:hover:bg-slate-700',
                        'rounded-lg transition-colors'
                      )}
                    >
                      <ChevronRight className="w-4 h-4 text-slate-500 dark:text-slate-400" />
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
};
