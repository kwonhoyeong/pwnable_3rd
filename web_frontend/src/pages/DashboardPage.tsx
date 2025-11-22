import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { AlertCircle, Clock } from 'lucide-react';
import { SearchBar } from '../components/dashboard/SearchBar';
import { StatsCards } from '../components/dashboard/StatsCards';
import { RiskDistributionChart } from '../components/dashboard/RiskDistributionChart';
import { RecentScansTable, ScanRecord } from '../components/dashboard/RecentScansTable';
import { Card } from '../components/ui/Card';
import {
  queryAPI,
  StatsResponse,
  HistoryResponse,
  QueryResponse,
  convertCVEDetailsToScanRecords,
  convertHistoryToScanRecords,
  getErrorCode,
  getErrorMessage,
} from '../api/endpoints';

/**
 * DashboardPage Component
 * Displays security overview with real-time vulnerability analysis
 */
export const DashboardPage: React.FC = () => {
  // Search state
  const [searchParams, setSearchParams] = useState<{ package: string; version: string } | null>(
    null
  );

  // ============================================================================
  // REACT-QUERY HOOKS
  // ============================================================================

  /**
   * Stats Query - Fetch vulnerability statistics
   */
  const statsQuery = useQuery<StatsResponse>({
    queryKey: ['stats'],
    queryFn: () => queryAPI.stats().then((res) => res.data),
    staleTime: 1000 * 60 * 5, // 5 minutes
    refetchInterval: 1000 * 60 * 2, // Refetch every 2 minutes
  });

  /**
   * History Query - Fetch recent scan history
   */
  const historyQuery = useQuery<HistoryResponse>({
    queryKey: ['history', 0, 10],
    queryFn: () => queryAPI.history(0, 10).then((res) => res.data),
    staleTime: 1000 * 60 * 5, // 5 minutes
    refetchInterval: 1000 * 60 * 2, // Refetch every 2 minutes
  });

  /**
   * Search Query - Fetch search results when user searches
   */
  const searchQuery = useQuery<QueryResponse>({
    queryKey: ['search', searchParams],
    queryFn: () => {
      if (!searchParams) {
        return Promise.reject(new Error('No search params'));
      }
      return queryAPI.query({ package: searchParams.package }).then((res) => res.data);
    },
    enabled: !!searchParams, // Only run when searchParams is not null
    staleTime: 1000 * 60 * 10, // 10 minutes
  });

  // ============================================================================
  // HANDLERS
  // ============================================================================

  /**
   * Handle search submission
   */
  const handleSearch = (packageName: string, version: string) => {
    setSearchParams({ package: packageName, version });
  };

  /**
   * Clear search results
   */
  const handleClearSearch = () => {
    setSearchParams(null);
  };

  // ============================================================================
  // DATA PROCESSING
  // ============================================================================

  // Extract stats data with fallbacks
  const stats = {
    totalScans: statsQuery.data?.total_scans ?? 0,
    critical: statsQuery.data?.risk_distribution.CRITICAL ?? 0,
    high: statsQuery.data?.risk_distribution.HIGH ?? 0,
    medium: statsQuery.data?.risk_distribution.MEDIUM ?? 0,
    low: statsQuery.data?.risk_distribution.LOW ?? 0,
  };

  // Risk distribution for chart
  const riskDistribution = statsQuery.data?.risk_distribution ?? {
    CRITICAL: 0,
    HIGH: 0,
    MEDIUM: 0,
    LOW: 0,
    Unknown: 0,
  };

  // Determine which scans to display: search results or history
  const displayedScans: ScanRecord[] = searchQuery.data
    ? convertCVEDetailsToScanRecords(searchQuery.data.cve_list)
    : convertHistoryToScanRecords(historyQuery.data?.records ?? []);

  // ============================================================================
  // RENDER
  // ============================================================================

  return (
    <div className="space-y-8">
      {/* Header Section */}
      <div>
        <h1 className="text-4xl font-bold text-slate-900 dark:text-white">Security Overview</h1>
        <p className="text-slate-600 dark:text-slate-400 mt-2">
          Real-time analysis of your NPM supply chain
        </p>
      </div>

      {/* Search Section */}
      <SearchBar onSearch={handleSearch} isLoading={searchQuery.isFetching} />

      {/* Error Messages */}
      {statsQuery.isError && (
        <div className="flex items-center gap-3 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
          <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400 flex-shrink-0" />
          <div>
            <p className="font-medium text-red-800 dark:text-red-200">Failed to load statistics</p>
            <p className="text-sm text-red-700 dark:text-red-300">Please try again later</p>
          </div>
        </div>
      )}

      {historyQuery.isError && !searchParams && (
        <div className="flex items-center gap-3 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
          <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400 flex-shrink-0" />
          <div>
            <p className="font-medium text-red-800 dark:text-red-200">Failed to load history</p>
            <p className="text-sm text-red-700 dark:text-red-300">Please try again later</p>
          </div>
        </div>
      )}

      {searchQuery.isError && searchParams && (
        (() => {
          const errorCode = getErrorCode(searchQuery.error);
          const isAnalysisInProgress = errorCode === 'ANALYSIS_IN_PROGRESS';

          return (
            <div
              className={`flex items-center gap-3 p-4 rounded-lg border ${
                isAnalysisInProgress
                  ? 'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800'
                  : 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800'
              }`}
            >
              {isAnalysisInProgress ? (
                <Clock className="w-5 h-5 text-blue-600 dark:text-blue-400 flex-shrink-0 animate-spin" />
              ) : (
                <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400 flex-shrink-0" />
              )}

              <div>
                {isAnalysisInProgress ? (
                  <>
                    <p className="font-medium text-blue-800 dark:text-blue-200">
                      AI Analysis In Progress
                    </p>
                    <p className="text-sm text-blue-700 dark:text-blue-300">
                      {getErrorMessage(searchQuery.error)}
                    </p>
                  </>
                ) : (
                  <>
                    <p className="font-medium text-red-800 dark:text-red-200">
                      Failed to search for {searchParams.package}
                    </p>
                    <p className="text-sm text-red-700 dark:text-red-300">
                      {getErrorMessage(searchQuery.error) || 'Please check the package name and try again'}
                    </p>
                  </>
                )}
              </div>
            </div>
          );
        })()
      )}

      {/* Stats Cards Section */}
      <StatsCards
        totalScans={stats.totalScans}
        critical={stats.critical}
        high={stats.high}
        medium={stats.medium}
        low={stats.low}
        isLoading={statsQuery.isLoading}
      />

      {/* Main Content Grid - Hidden when analysis is in progress */}
      {!(() => {
        const errorCode = getErrorCode(searchQuery.error);
        return errorCode === 'ANALYSIS_IN_PROGRESS' && searchParams;
      })() && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column: Risk Distribution Chart (1/3 width) */}
          <div className="lg:col-span-1">
            <RiskDistributionChart data={riskDistribution} isLoading={statsQuery.isLoading} />
          </div>

          {/* Right Column: Recent Scans Table (2/3 width) */}
          <div className="lg:col-span-2">
            <RecentScansTable
              data={displayedScans}
              isLoading={
                searchQuery.isFetching || (historyQuery.isLoading && !searchParams)
              }
            />
          </div>
        </div>
      )}

      {/* Search Results Information */}
      {searchParams && searchQuery.data && (
        <Card className="bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium text-blue-900 dark:text-blue-100">
                Found {searchQuery.data.cve_list.length} vulnerabilities for{' '}
                <span className="font-semibold">{searchParams.package}</span>
              </p>
              <p className="text-sm text-blue-700 dark:text-blue-300 mt-1">
                Version: {searchParams.version}
              </p>
            </div>
            <button
              onClick={handleClearSearch}
              className="px-4 py-2 text-sm font-medium text-blue-700 dark:text-blue-300 hover:bg-blue-100 dark:hover:bg-blue-900/40 rounded-lg transition-colors"
            >
              Clear Search
            </button>
          </div>
        </Card>
      )}

      {/* No Results Message */}
      {searchParams && searchQuery.data && searchQuery.data.cve_list.length === 0 && (
        <Card className="bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800">
          <p className="text-green-800 dark:text-green-200">
            ✓ No vulnerabilities found for <span className="font-semibold">{searchParams.package}</span>
          </p>
        </Card>
      )}
    </div>
  );
};
