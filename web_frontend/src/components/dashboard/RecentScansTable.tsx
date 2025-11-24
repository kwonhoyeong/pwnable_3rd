import React from 'react';
import { Link } from 'react-router-dom';
import { Card } from '../ui/Card';
import { Badge } from '../ui/Badge';
import { ChevronRight, FileText } from 'lucide-react';
import { clsx } from 'clsx';

import { ScanRecord } from '../../api/endpoints';

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

  const formatDate = (dateString: string | null | undefined) => {
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
    <Card title="최근 취약점 보고서" className="overflow-hidden">
      {isLoading ? (
        <div className="space-y-3">
          {[...Array(5)].map((_, i) => (
            <div
              key={i}
              className="h-16 rounded animate-pulse"
              style={{ backgroundColor: 'var(--color-bg-tertiary)' }}
            />
          ))}
        </div>
      ) : data.length === 0 ? (
        <div
          className="text-center py-12"
          style={{ color: 'var(--color-text-tertiary)' }}
        >
          <FileText className="w-12 h-12 mx-auto mb-3 opacity-50" />
          <p>취약점 보고서가 없습니다</p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr
                className="border-b"
                style={{ borderColor: 'var(--color-border)' }}
              >
                <th
                  className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-white"
                >
                  분석 정보
                </th>
                <th
                  className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-white"
                >
                  위험도
                </th>
                <th
                  className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-white"
                >
                  점수
                </th>
                <th
                  className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-white"
                >
                  요약
                </th>
                <th
                  className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-white"
                >
                  날짜
                </th>
                <th
                  className="px-4 py-3 text-center text-xs font-medium uppercase tracking-wider text-white"
                >
                  상세보기
                </th>
              </tr>
            </thead>
            <tbody className="divide-y" style={{ borderColor: 'var(--color-border)' }}>
              {data.map((scan) => (
                <tr
                  key={scan.cve_id}
                  className="transition-colors hover:bg-opacity-50"
                  style={{
                    '--hover-bg': 'var(--color-bg-tertiary)',
                  } as React.CSSProperties}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.backgroundColor = 'var(--color-bg-tertiary)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.backgroundColor = 'transparent';
                  }}
                >
                  <td
                    className="px-4 py-4 text-sm font-mono"
                    style={{ color: 'var(--color-text-primary)' }}
                  >
                    {scan.cve_id}
                  </td>
                  <td className="px-4 py-4">
                    <Badge variant={getRiskVariant(scan.risk_level)}>
                      {scan.risk_level}
                    </Badge>
                  </td>
                  <td
                    className="px-4 py-4 text-sm font-semibold"
                    style={{ color: 'var(--color-text-secondary)' }}
                  >
                    {typeof scan.risk_score === 'number' ? scan.risk_score.toFixed(1) : 'N/A'}
                  </td>
                  <td
                    className="px-4 py-4 text-sm max-w-xs truncate"
                    style={{ color: 'var(--color-text-secondary)' }}
                  >
                    {scan.analysis_summary || '요약 정보가 없습니다'}
                  </td>
                  <td
                    className="px-4 py-4 text-sm"
                    style={{ color: 'var(--color-text-tertiary)' }}
                  >
                    {formatDate(scan.created_at)}
                  </td>
                  <td className="px-4 py-4 text-center">
                    <Link
                      to={`/report/${scan.cve_id}`}
                      className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium rounded
                                 transition-all hover-lift"
                      style={{
                        backgroundColor: 'var(--color-bg-elevated)',
                        color: 'var(--color-text-primary)',
                        border: '1px solid var(--color-border)',
                      }}
                    >
                      보고서 보기
                      <ChevronRight className="w-3 h-3" />
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
