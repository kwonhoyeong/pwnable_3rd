import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { AlertCircle, Clock } from 'lucide-react';
import { SearchBar } from '../components/dashboard/SearchBar';
import { StatsCards } from '../components/dashboard/StatsCards';

import { RecentScansTable } from '../components/dashboard/RecentScansTable';
import { Card } from '../components/ui/Card';
import {
  queryAPI,
  StatsResponse,
  HistoryResponse,
  QueryResponse,
  ScanRecord,
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
  const [searchParams, setSearchParams] = useState<{ package: string; version: string; ecosystem: string } | null>(
    null
  );
  const [selectedEcosystem, setSelectedEcosystem] = useState<string>('npm');

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
      // Pass package, version, and ecosystem to the backend
      return queryAPI.query({
        package: searchParams.package,
        version: searchParams.version || 'latest', // Default to 'latest' if not specified
        ecosystem: searchParams.ecosystem,
      }).then((res) => res.data);
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
    // Check if it's a CVE ID search
    if (packageName.toUpperCase().startsWith('CVE-')) {
      // For CVE search, ecosystem doesn't matter as much, but we pass it anyway
      // Ideally backend handles CVE search regardless of ecosystem
      setSearchParams({ package: packageName, version, ecosystem: selectedEcosystem });
    } else {
      setSearchParams({ package: packageName, version, ecosystem: selectedEcosystem });
    }
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
    critical: statsQuery.data?.risk_distribution?.CRITICAL ?? 0,
    high: statsQuery.data?.risk_distribution?.HIGH ?? 0,
    medium: statsQuery.data?.risk_distribution?.MEDIUM ?? 0,
    low: statsQuery.data?.risk_distribution?.LOW ?? 0,
  };

  // Determine which scans to display: search results or history
  const displayedScans: ScanRecord[] = searchQuery.data?.cve_list
    ? convertCVEDetailsToScanRecords(searchQuery.data.cve_list)
    : convertHistoryToScanRecords(historyQuery.data?.records ?? []);

  // ============================================================================
  // RENDER
  // ============================================================================

  return (
    <div className="space-y-8">
      {/* Header Section */}


      {/* Search Section */}
      <SearchBar
        onSearch={handleSearch}
        isLoading={searchQuery.isLoading}
        ecosystem={selectedEcosystem}
        onEcosystemChange={setSelectedEcosystem}
      />

      {/* Error Messages */}
      {statsQuery.isError && (
        <div
          className="flex items-center gap-3 p-4 rounded-lg border"
          style={{
            backgroundColor: 'rgba(220, 38, 38, 0.05)',
            borderColor: 'rgba(220, 38, 38, 0.2)',
            color: 'var(--color-critical)',
          }}
        >
          <AlertCircle className="w-5 h-5 flex-shrink-0" />
          <div>
            <p className="font-medium">Failed to load statistics</p>
            <p className="text-sm opacity-80">Please try again later</p>
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
              className={`flex items-center gap-3 p-4 rounded-lg border ${isAnalysisInProgress
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
                      보고서 생성 중... (Generating Report...)
                    </p>
                    <p className="text-sm text-blue-700 dark:text-blue-300">
                      잠시만 기다려주세요. AI가 취약점을 분석하고 있습니다. (Please wait a moment. AI is analyzing vulnerabilities.)
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
          <div className="grid grid-cols-1 gap-6">
            <RecentScansTable
              data={displayedScans}
              isLoading={
                searchQuery.isFetching || (historyQuery.isLoading && !searchParams)
              }
            />
          </div>
        )}

      {/* Search Results Information */}
      {searchParams && searchQuery.data && (
        <Card className="bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium text-blue-900 dark:text-blue-100">
                Found {searchQuery.data.cve_list?.length ?? 0} vulnerabilities for{' '}
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
      {searchParams && searchQuery.data && searchQuery.data.cve_list?.length === 0 && (
        <Card className="bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800">
          <p className="text-green-800 dark:text-green-200">
            ✓ No vulnerabilities found for <span className="font-semibold">{searchParams.package}</span>
          </p>
        </Card>
      )}
    </div>
  );
};
