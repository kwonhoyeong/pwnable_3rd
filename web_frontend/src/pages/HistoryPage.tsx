import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { AlertCircle, ChevronLeft, ChevronRight } from 'lucide-react';
import { queryAPI, HistoryResponse, convertHistoryToScanRecords } from '../api/endpoints';
import { RecentScansTable } from '../components/dashboard/RecentScansTable';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';

/**
 * HistoryPage Component
 * Displays paginated analysis history with vulnerability scan records
 */
export const HistoryPage: React.FC = () => {
  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 10;
  const skip = (currentPage - 1) * itemsPerPage;

  // ============================================================================
  // REACT-QUERY HOOK
  // ============================================================================

  /**
   * Fetch paginated history from backend
   */
  const { data, isLoading, isError } = useQuery<HistoryResponse>({
    queryKey: ['history', skip, itemsPerPage],
    queryFn: () =>
      queryAPI.history(skip, itemsPerPage).then((res) => res.data),
    staleTime: 1000 * 60 * 5, // 5 minutes
  });

  // ============================================================================
  // DATA PROCESSING
  // ============================================================================

  // Extract history records and convert to display format
  const historyRecords = data?.records ?? [];
  const displayedScans = convertHistoryToScanRecords(historyRecords);
  const totalReturned = data?.total_returned ?? 0;
  const hasNextPage = totalReturned >= itemsPerPage;
  const hasPreviousPage = currentPage > 1;

  // ============================================================================
  // HANDLERS
  // ============================================================================

  const handleNextPage = () => {
    if (hasNextPage) {
      setCurrentPage((prev) => prev + 1);
      // Scroll to top of table
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  };

  const handlePreviousPage = () => {
    if (hasPreviousPage) {
      setCurrentPage((prev) => prev - 1);
      // Scroll to top of table
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  };

  // ============================================================================
  // RENDER
  // ============================================================================

  return (
    <div className="space-y-8">
      {/* Header Section */}
      <div>
        <h1 className="text-4xl font-bold text-white">
          분석 히스토리
        </h1>
        <p className="text-white mt-2">
          이전 취약점 스캔 및 분석 결과를 확인하세요
        </p>
      </div>

      {/* Error Message */}
      {isError && (
        <div className="flex items-center gap-3 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
          <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400 flex-shrink-0" />
          <div>
            <p className="font-medium text-red-800 dark:text-red-200">
              히스토리를 불러오는데 실패했습니다
            </p>
            <p className="text-sm text-red-700 dark:text-red-300">
              잠시 후 다시 시도하거나 페이지를 새로고침하세요
            </p>
          </div>
        </div>
      )}

      {/* History Table */}
      <RecentScansTable
        data={displayedScans}
        isLoading={isLoading}
      />

      {/* Pagination Section */}
      {!isLoading && totalReturned > 0 && (
        <div className="space-y-4">
          {/* Pagination Controls */}
          <div className="flex items-center justify-between">
            <div className="text-sm text-slate-600 dark:text-slate-400">
              페이지 <span className="font-semibold">{currentPage}</span>
              {hasNextPage && (
                <span>
                  {' '}
                  ({totalReturned}+ 건 중 {displayedScans.length} 건 표시)
                </span>
              )}
            </div>

            {/* Navigation Buttons */}
            <div className="flex gap-3">
              <Button
                variant="secondary"
                size="sm"
                disabled={!hasPreviousPage}
                onClick={handlePreviousPage}
              >
                <ChevronLeft className="w-4 h-4" />
                이전
              </Button>

              <Button
                variant="secondary"
                size="sm"
                disabled={!hasNextPage}
                onClick={handleNextPage}
              >
                다음
                <ChevronRight className="w-4 h-4" />
              </Button>
            </div>
          </div>

          {/* No More Results Info */}
          {!hasNextPage && currentPage > 1 && (
            <Card className="bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800">
              <p className="text-sm text-blue-800 dark:text-blue-200">
                히스토리의 끝입니다. 이 페이지에 {displayedScans.length} 건의 결과가 표시됩니다.
              </p>
            </Card>
          )}
        </div>
      )}

      {/* Empty State */}
      {!isLoading && totalReturned === 0 && (
        <Card className="bg-slate-50 dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-center py-12">
          <p className="text-slate-600 dark:text-slate-400">
            히스토리에 취약점 스캔 기록이 없습니다.
          </p>
          <p className="text-sm text-slate-500 dark:text-slate-500 mt-1">
            대시보드에서 패키지를 검색하여 시작하세요.
          </p>
        </Card>
      )}
    </div>
  );
};
