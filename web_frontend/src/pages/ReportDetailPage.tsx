import React from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import ReactMarkdown from 'react-markdown';
import { Components } from 'react-markdown';
import { ArrowLeft, AlertCircle, Shield, Target, ListChecks, Loader } from 'lucide-react';
import { queryAPI, CVEDetail } from '../api/endpoints';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';

/**
 * ReportDetailPage Component
 * Displays detailed analysis of a specific CVE vulnerability
 */
export const ReportDetailPage: React.FC = () => {
  const { cveId } = useParams<{ cveId: string }>();

  // ============================================================================
  // REACT-QUERY HOOK
  // ============================================================================

  /**
   * Fetch CVE detail from backend
   */
  const { data, isLoading, isError } = useQuery({
    queryKey: ['report', cveId],
    queryFn: () => {
      if (!cveId) {
        return Promise.reject(new Error('No CVE ID provided'));
      }
      return queryAPI.searchByCVE(cveId).then((res) => res.data);
    },
    enabled: !!cveId,
    staleTime: 1000 * 60 * 10, // 10 minutes
  });

  // ============================================================================
  // DATA EXTRACTION
  // ============================================================================

  // Extract the first CVE from the list (API returns cve_list array)
  const cveData: CVEDetail | undefined = data?.cve_list?.[0];

  // ============================================================================
  // MARKDOWN CUSTOM COMPONENTS (Typography Enhancement)
  // ============================================================================

  /**
   * Custom ReactMarkdown components for enhanced readability
   */
  const markdownComponents: Components = {
    // Headings: Clear hierarchy with generous spacing
    h1: ({ node, ...props }) => (
      <h1 className="text-3xl font-bold text-white mt-8 mb-4 pb-2 border-b-2 border-slate-700" {...props} />
    ),
    h2: ({ node, ...props }) => (
      <h2 className="text-2xl font-semibold text-white mt-8 mb-4" {...props} />
    ),
    h3: ({ node, ...props }) => (
      <h3 className="text-xl font-semibold text-white mt-6 mb-3" {...props} />
    ),
    h4: ({ node, ...props }) => (
      <h4 className="text-lg font-semibold text-white mt-5 mb-2" {...props} />
    ),

    // Paragraphs: Wide line spacing, generous bottom margin
    p: ({ node, ...props }) => (
      <p className="leading-loose mb-4 text-white" {...props} />
    ),

    // Lists: Clear spacing between items
    ul: ({ node, ...props }) => (
      <ul className="space-y-2 my-4 ml-6 list-disc marker:text-blue-400" {...props} />
    ),
    ol: ({ node, ...props }) => (
      <ol className="space-y-2 my-4 ml-6 list-decimal marker:text-blue-400" {...props} />
    ),
    li: ({ node, ...props }) => (
      <li className="leading-relaxed pl-2 text-white" {...props} />
    ),

    // Code blocks: Dark background with padding
    pre: ({ node, ...props }) => (
      <pre className="bg-slate-950 text-slate-100 p-4 rounded-lg overflow-x-auto my-5 border border-slate-700" {...props} />
    ),
    code: ({ node, inline, ...props }) =>
      inline ? (
        <code className="bg-slate-800 text-blue-400 px-1.5 py-0.5 rounded text-sm font-mono" {...props} />
      ) : (
        <code className="font-mono text-sm" {...props} />
      ),

    // Blockquotes: Left border with background
    blockquote: ({ node, ...props }) => (
      <blockquote className="border-l-4 border-blue-500 bg-blue-900/20 pl-4 py-3 my-5 italic text-white" {...props} />
    ),

    // Strong/Bold: Emphasis color
    strong: ({ node, ...props }) => (
      <strong className="font-bold text-white" {...props} />
    ),

    // Links: Distinctive styling
    a: ({ node, ...props }) => (
      <a className="text-blue-400 hover:underline font-medium" {...props} />
    ),

    // Horizontal rule: Subtle divider
    hr: ({ node, ...props }) => (
      <hr className="my-8 border-slate-600" {...props} />
    ),

    // Tables: Structured presentation
    table: ({ node, ...props }) => (
      <div className="overflow-x-auto my-5">
        <table className="min-w-full divide-y divide-slate-600" {...props} />
      </div>
    ),
    thead: ({ node, ...props }) => (
      <thead className="bg-slate-800" {...props} />
    ),
    tbody: ({ node, ...props }) => (
      <tbody className="divide-y divide-slate-700" {...props} />
    ),
    tr: ({ node, ...props }) => (
      <tr className="hover:bg-slate-800/50" {...props} />
    ),
    th: ({ node, ...props }) => (
      <th className="px-4 py-3 text-left text-sm font-semibold text-white" {...props} />
    ),
    td: ({ node, ...props }) => (
      <td className="px-4 py-3 text-sm text-white" {...props} />
    ),
  };

  // ============================================================================
  // HELPER FUNCTIONS
  // ============================================================================

  const getRiskScoreColor = (score: number): string => {
    if (score >= 9.0) return 'text-sentinel-error';
    if (score >= 7.0) return 'text-sentinel-warning';
    if (score >= 5.0) return 'text-sentinel-primary';
    return 'text-sentinel-success';
  };

  const getRiskVariant = (level: string): 'critical' | 'high' | 'medium' | 'low' | 'default' => {
    switch (level.toLowerCase()) {
      case 'critical': return 'critical';
      case 'high': return 'high';
      case 'medium': return 'medium';
      case 'low': return 'low';
      default: return 'default';
    }
  };

  // ============================================================================
  // RENDER: LOADING STATE
  // ============================================================================

  if (isLoading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="flex items-center gap-4 mb-8">
          <div className="h-10 w-10 bg-sentinel-surface rounded-lg" />
          <div className="h-12 w-80 bg-sentinel-surface rounded" />
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            <div className="h-96 bg-sentinel-surface rounded-2xl border border-white/5" />
          </div>
          <div className="space-y-6">
            <div className="h-40 bg-sentinel-surface rounded-2xl border border-white/5" />
            <div className="h-40 bg-sentinel-surface rounded-2xl border border-white/5" />
          </div>
        </div>
      </div>
    );
  }

  // ============================================================================
  // RENDER: ERROR STATE
  // ============================================================================

  if (isError || !cveData) {
    return (
      <div className="space-y-6">
        <Link to="/">
          <Button variant="secondary" size="sm" className="bg-sentinel-surface hover:bg-sentinel-primary/20 text-white border border-white/10">
            <ArrowLeft className="w-4 h-4" />
            Back to Dashboard
          </Button>
        </Link>
        <div className="flex items-center gap-3 p-6 bg-sentinel-error/10 border border-sentinel-error/30 rounded-lg">
          <AlertCircle className="w-6 h-6 text-sentinel-error flex-shrink-0" />
          <div>
            <p className="font-semibold text-sentinel-error">CVE Not Found</p>
            <p className="text-sm text-sentinel-error/80 mt-1">
              Unable to load details for {cveId}. Please check the CVE ID and try again.
            </p>
          </div>
        </div>
      </div>
    );
  }

  // ============================================================================
  // RENDER: SUCCESS STATE
  // ============================================================================

  return (
    <div className="space-y-6 animate-fade-in">
      <Link to="/">
        <Button variant="secondary" size="sm" className="bg-sentinel-surface hover:bg-sentinel-primary/20 text-white border border-white/10">
          <ArrowLeft className="w-4 h-4" />
          Back to Dashboard
        </Button>
      </Link>

      <div className="flex items-start justify-between gap-6 pb-6 border-b border-white/10">
        <div>
          <h1 className="text-4xl font-bold text-white font-heading">{cveData.cve_id}</h1>
          <p className="text-sentinel-text-muted mt-2">Vulnerability Analysis & Recommendations</p>
        </div>
        <Badge variant={getRiskVariant(cveData.risk_level)} className="text-lg px-4 py-2">
          {cveData.risk_level}
        </Badge>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Analysis Report */}
        <div className="lg:col-span-2 space-y-6">
          <Card title="Analysis Report">
            <div className="prose-custom max-w-none text-sentinel-text-main">
              <ReactMarkdown components={markdownComponents}>
                {cveData.analysis_summary || 'No analysis available'}
              </ReactMarkdown>
            </div>
          </Card>
        </div>

        {/* Right Column: Sidebar Metrics */}
        <div className="space-y-6">
          <Card title="Risk Score">
            <div className="space-y-3">
              <div className="flex items-baseline gap-2">
                <span className={`text-5xl font-bold ${getRiskScoreColor(cveData.risk_score)}`}>
                  {cveData.risk_score.toFixed(1)}
                </span>
                <span className="text-sm text-sentinel-text-muted">/ 10</span>
              </div>
              <p className="text-sm text-sentinel-text-muted">
                Priority: <span className="font-semibold text-white">{cveData.risk_label}</span>
              </p>
              <div className="h-2 bg-sentinel-surface rounded-full overflow-hidden border border-white/5">
                <div
                  className={`h-full rounded-full ${cveData.risk_score >= 9.0 ? 'bg-sentinel-error shadow-neon-red' :
                      cveData.risk_score >= 7.0 ? 'bg-sentinel-warning shadow-neon-orange' :
                        cveData.risk_score >= 5.0 ? 'bg-sentinel-primary shadow-neon-blue' :
                          'bg-sentinel-success shadow-neon-green'
                    }`}
                  style={{ width: `${(cveData.risk_score / 10) * 100}%` }}
                />
              </div>
            </div>
          </Card>

          <Card title="Technical Metrics">
            <div className="space-y-4">
              <div className="flex items-center justify-between p-3 bg-sentinel-surface/50 rounded-lg border border-white/5">
                <div className="flex items-center gap-2">
                  <Target className="w-4 h-4 text-sentinel-text-muted" />
                  <span className="text-sm font-medium text-sentinel-text-muted">CVSS Score</span>
                </div>
                <span className="text-lg font-semibold text-white">
                  {cveData.cvss_score !== null ? cveData.cvss_score.toFixed(1) : 'N/A'}
                </span>
              </div>

              <div className="flex items-center justify-between p-3 bg-sentinel-surface/50 rounded-lg border border-white/5">
                <div className="flex items-center gap-2">
                  <Shield className="w-4 h-4 text-sentinel-text-muted" />
                  <span className="text-sm font-medium text-sentinel-text-muted">EPSS Score</span>
                </div>
                <span className="text-lg font-semibold text-white">
                  {cveData.epss_score !== null ? (cveData.epss_score * 100).toFixed(1) + '%' : 'N/A'}
                </span>
              </div>

              <div className="flex items-center justify-between p-3 bg-sentinel-surface/50 rounded-lg border border-white/5">
                <span className="text-sm font-medium text-sentinel-text-muted">Risk Level</span>
                <Badge variant={getRiskVariant(cveData.risk_level)}>{cveData.risk_level}</Badge>
              </div>
            </div>
          </Card>

          {cveData.recommendations && cveData.recommendations.length > 0 && (
            <Card title="Recommendations">
              <ul className="space-y-3">
                {cveData.recommendations.map((rec, idx) => (
                  <li key={idx} className="flex gap-3 text-sm">
                    <ListChecks className="w-4 h-4 text-sentinel-primary flex-shrink-0 mt-0.5" />
                    <span className="text-white">{rec}</span>
                  </li>
                ))}
              </ul>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
};
