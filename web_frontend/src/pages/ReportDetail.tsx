import React from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { queryAPI } from '../api/endpoints';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { ArrowLeft } from 'lucide-react';
import ReactMarkdown from 'react-markdown';

export const ReportDetail: React.FC = () => {
  const { cveId } = useParams<{ cveId: string }>();
  const navigate = useNavigate();

  const { data, isLoading, error } = useQuery({
    queryKey: ['report', cveId],
    queryFn: () => cveId ? queryAPI.query({ cve_id: cveId }) : Promise.reject('No CVE ID'),
    enabled: !!cveId,
    select: (res) => res.data,
  });

  if (!cveId) {
    return <div className="p-8">CVE ID not found</div>;
  }

  if (isLoading) return <div className="p-8">Loading report...</div>;
  if (error) return <div className="p-8 text-red-600">Error loading report</div>;

  const report = Array.isArray(data) ? data[0] : null;

  return (
    <div className="space-y-8">
      <div className="flex items-center gap-4">
        <Button variant="secondary" size="sm" onClick={() => navigate(-1)}>
          <ArrowLeft className="w-4 h-4" />
        </Button>
        <h1 className="text-3xl font-bold">{cveId}</h1>
      </div>

      {report && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            <Card title="Executive Summary">
              <ReactMarkdown className="prose prose-sm max-w-none">
                {report.analysis_summary || 'No summary available'}
              </ReactMarkdown>
            </Card>

            {report.recommendations && report.recommendations.length > 0 && (
              <Card title="Recommendations">
                <ul className="space-y-2">
                  {report.recommendations.map((rec: string, idx: number) => (
                    <li key={idx} className="flex gap-2">
                      <span className="text-blue-600">•</span>
                      <span>{rec}</span>
                    </li>
                  ))}
                </ul>
              </Card>
            )}
          </div>

          <div className="space-y-6">
            <Card title="Risk Assessment">
              <div className="space-y-4">
                {report.risk_level && (
                  <div>
                    <p className="text-sm text-slate-600 mb-2">Risk Level</p>
                    <Badge variant={report.risk_level.toLowerCase() as any}>
                      {report.risk_level}
                    </Badge>
                  </div>
                )}
                {report.cvss_score && (
                  <div>
                    <p className="text-sm text-slate-600 mb-2">CVSS Score</p>
                    <p className="text-2xl font-bold">{report.cvss_score}</p>
                  </div>
                )}
                {report.epss_score && (
                  <div>
                    <p className="text-sm text-slate-600 mb-2">EPSS Score</p>
                    <p className="text-2xl font-bold">{report.epss_score}</p>
                  </div>
                )}
              </div>
            </Card>
          </div>
        </div>
      )}
    </div>
  );
};
