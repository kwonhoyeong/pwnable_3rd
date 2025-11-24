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

  /**
   * Determine risk score color based on risk_score
   */
  const getRiskScoreColor = (score: number): string => {
    if (score >= 9.0) return 'text-critical-600 dark:text-critical-400';
    if (score >= 7.0) return 'text-high-600 dark:text-high-400';
    if (score >= 5.0) return 'text-medium-600 dark:text-medium-400';
    return 'text-low-600 dark:text-low-400';
  };

  /**
   * Get badge variant for risk level
   */
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

  // ============================================================================
  // RENDER: LOADING STATE
  // ============================================================================

  if (isLoading) {
    return (
      <div className="space-y-6">
        {/* Header Skeleton */}
        <div className="flex items-center gap-4 mb-8">
          <div className="h-10 w-10 bg-slate-200 dark:bg-slate-700 rounded-lg animate-pulse" />
          <div className="h-12 w-80 bg-slate-200 dark:bg-slate-700 rounded animate-pulse" />
        </div>

        {/* Content Grid Skeleton */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column */}
          <div className="lg:col-span-2 space-y-6">
            <Card>
              <div className="h-96 bg-slate-200 dark:bg-slate-700 rounded animate-pulse" />
            </Card>
          </div>

          {/* Right Column */}
          <div className="space-y-6">
            <Card>
              <div className="h-40 bg-slate-200 dark:bg-slate-700 rounded animate-pulse" />
            </Card>
            <Card>
              <div className="h-40 bg-slate-200 dark:bg-slate-700 rounded animate-pulse" />
            </Card>
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
        {/* Back Button */}
        <Link to="/">
          <Button variant="secondary" size="sm">
            <ArrowLeft className="w-4 h-4" />
            Back to Dashboard
          </Button>
        </Link>

        {/* Error Message */}
        <div className="flex items-center gap-3 p-6 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
          <AlertCircle className="w-6 h-6 text-red-600 dark:text-red-400 flex-shrink-0" />
          <div>
            <p className="font-semibold text-red-800 dark:text-red-200">CVE Not Found</p>
            <p className="text-sm text-red-700 dark:text-red-300 mt-1">
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
    <div className="space-y-6">
      {/* Back Button */}
      <Link to="/">
        <Button variant="secondary" size="sm">
          <ArrowLeft className="w-4 h-4" />
          Back to Dashboard
        </Button>
      </Link>

      {/* Header Section */}
      <div className="flex items-start justify-between gap-6 pb-6 border-b border-slate-200 dark:border-slate-700">
        <div>
          <h1 className="text-4xl font-bold text-white">{cveData.cve_id}</h1>
          <p className="text-slate-400 mt-2">Vulnerability Analysis & Recommendations</p>
        </div>
        <Badge variant={getRiskVariant(cveData.risk_level)} className="text-lg px-4 py-2">
          {cveData.risk_level}
        </Badge>
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Analysis Report (2/3 width) */}
        <div className="lg:col-span-2 space-y-6">
          {/* Analysis Report Card */}
          <Card title="Analysis Report">
            {/* Enhanced Markdown Rendering with Custom Typography */}
            <div className="prose-custom max-w-none">
              <ReactMarkdown components={markdownComponents}>
                {cveData.analysis_summary || 'No analysis available'}
              </ReactMarkdown>
            </div>
          </Card>
        </div>

        {/* Right Column: Sidebar Metrics (1/3 width) */}
        <div className="space-y-6">
          {/* Risk Score Card */}
          <Card title="Risk Score">
            <div className="space-y-3">
              <div className="flex items-baseline gap-2">
                <span className={`text-5xl font-bold ${getRiskScoreColor(cveData.risk_score)}`}>
                  {cveData.risk_score.toFixed(1)}
                </span>
                <span className="text-sm text-slate-600 dark:text-slate-400">/ 10</span>
              </div>
              <p className="text-sm text-slate-600 dark:text-slate-400">
                Priority: <span className="font-semibold">{cveData.risk_label}</span>
              </p>
              <div className="h-2 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full ${cveData.risk_score >= 9.0
                    ? 'bg-critical-600'
                    : cveData.risk_score >= 7.0
                      ? 'bg-high-600'
                      : cveData.risk_score >= 5.0
                        ? 'bg-medium-600'
                        : 'bg-low-600'
                    }`}
                  style={{ width: `${(cveData.risk_score / 10) * 100}%` }}
                />
              </div>
            </div>
          </Card>

          {/* Technical Metrics Card */}
          <Card title="Technical Metrics">
            <div className="space-y-4">
              {/* CVSS Score */}
              <div className="flex items-center justify-between p-3 bg-slate-50 dark:bg-slate-800 rounded-lg">
                <div className="flex items-center gap-2">
                  <Target className="w-4 h-4 text-slate-500 dark:text-slate-400" />
                  <span className="text-sm font-medium text-slate-700 dark:text-slate-300">CVSS Score</span>
                </div>
                <span className="text-lg font-semibold text-slate-900 dark:text-white">
                  {cveData.cvss_score !== null ? cveData.cvss_score.toFixed(1) : 'N/A'}
                </span>
              </div>

              {/* EPSS Score */}
              <div className="flex items-center justify-between p-3 bg-slate-50 dark:bg-slate-800 rounded-lg">
                <div className="flex items-center gap-2">
                  <Shield className="w-4 h-4 text-slate-500 dark:text-slate-400" />
                  <span className="text-sm font-medium text-slate-700 dark:text-slate-300">EPSS Score</span>
                </div>
                <span className="text-lg font-semibold text-slate-900 dark:text-white">
                  {cveData.epss_score !== null ? (cveData.epss_score * 100).toFixed(1) + '%' : 'N/A'}
                </span>
              </div>

              {/* Risk Level */}
              <div className="flex items-center justify-between p-3 bg-slate-50 dark:bg-slate-800 rounded-lg">
                <span className="text-sm font-medium text-slate-700 dark:text-slate-300">Risk Level</span>
                <Badge variant={getRiskVariant(cveData.risk_level)}>{cveData.risk_level}</Badge>
              </div>
            </div>
          </Card>

          {/* Recommendations Card */}
          {cveData.recommendations && cveData.recommendations.length > 0 && (
            <Card title="Recommendations">
              <ul className="space-y-3">
                {cveData.recommendations.map((rec, idx) => (
                  <li key={idx} className="flex gap-3 text-sm">
                    <ListChecks className="w-4 h-4 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
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
