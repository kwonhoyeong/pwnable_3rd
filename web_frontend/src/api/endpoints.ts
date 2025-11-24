import { AxiosResponse } from 'axios';
import client from './client';

/**
 * ============================================================================
 * TYPE DEFINITIONS - Match backend models from query_api/app/models.py
 * ============================================================================
 */

/**
 * CVEDetail - Detailed information about a single CVE
 * Matches backend CVEDetail model exactly
 * Note: risk_score and risk_label are added by the service layer
 */
export interface CVEDetail {
  cve_id: string;
  epss_score: number | null;
  cvss_score: number | null;
  risk_level: string; // "CRITICAL", "HIGH", "MEDIUM", "LOW", "Unknown"
  analysis_summary: string; // Markdown formatted text
  recommendations: string[];
  risk_score: number; // Float - calculated by service (risk weight + cvss + epss)
  risk_label: string; // "P1", "P2", "P3"
}

/**
 * QueryResponse - Response from /api/v1/query endpoint
 * Wraps a list of CVEDetail objects returned from package or CVE search
 */
export interface QueryResponse {
  package?: string;
  cve_id?: string;
  cve_list: CVEDetail[];
}

/**
 * HistoryRecord - Individual record in history
 * Returned from /api/v1/history endpoint with nullable risk_score
 */
export interface HistoryRecord {
  cve_id: string;
  risk_level: string;
  risk_score: number | null; // Can be null from database
  analysis_summary: string;
  recommendations: string[];
  generated_at: string | null; // ISO 8601 timestamp or null
  created_at: string | null; // ISO 8601 timestamp or null
}

/**
 * HistoryResponse - Response from /api/v1/history endpoint
 * Paginated list of historical CVE scans
 */
export interface HistoryResponse {
  records: HistoryRecord[];
  skip: number;
  limit: number;
  total_returned: number;
}

/**
 * RiskDistribution - Risk level counts
 * Used in StatsResponse
 */
export interface RiskDistribution {
  CRITICAL: number;
  HIGH: number;
  MEDIUM: number;
  LOW: number;
  Unknown: number;
}

/**
 * StatsResponse - Response from /api/v1/stats endpoint
 * Aggregated vulnerability statistics
 */
export interface StatsResponse {
  total_scans: number;
  risk_distribution: RiskDistribution;
}

/**
 * HealthResponse - Response from /health endpoint
 * Health check status
 */
export interface HealthResponse {
  status: string;
  timestamp?: string;
}

/**
 * ============================================================================
 * API CLIENT FUNCTIONS
 * ============================================================================
 */

/**
 * Query API endpoints namespace
 * All functions return axios AxiosResponse for full control over data/headers
 */
export const queryAPI = {
  /**
   * Search for vulnerabilities by CVE ID
   * GET /api/v1/query?cve_id={cveId}
   *
   * @param cveId - CVE identifier (e.g., "CVE-2024-1234")
   * @returns Promise<QueryResponse> containing array of CVEDetail objects
   */
  searchByCVE: (cveId: string): Promise<AxiosResponse<QueryResponse>> =>
    client.get<QueryResponse>('/api/v1/query', {
      params: { cve_id: cveId },
    }),

  /**
   * Search for vulnerabilities by package name
   * GET /api/v1/query?package={packageName}
   *
   * @param packageName - NPM package name (e.g., "react", "lodash")
   * @returns Promise<QueryResponse> containing array of CVEDetail objects
   */
  searchByPackage: (packageName: string): Promise<AxiosResponse<QueryResponse>> =>
    client.get<QueryResponse>('/api/v1/query', {
      params: { package: packageName },
    }),

  /**
   * Generic query endpoint - supports both package and CVE ID search
   * GET /api/v1/query?package={packageName}&version={version}&cve_id={cveId}
   *
   * @param params - Query parameters { package?: string; version?: string; cve_id?: string }
   * @returns Promise<QueryResponse> containing array of CVEDetail objects
   *
   * Note: For package searches, version parameter is optional (defaults to "latest" on backend)
   */
  query: (params: { package?: string; version?: string; cve_id?: string }): Promise<AxiosResponse<QueryResponse>> =>
    client.get<QueryResponse>('/api/v1/query', { params }),

  /**
   * Get paginated analysis history
   * GET /api/v1/history?skip={skip}&limit={limit}
   *
   * @param skip - Number of records to skip (default: 0)
   * @param limit - Number of records to fetch (default: 10, max: 100)
   * @returns Promise<HistoryResponse> containing paginated history records
   */
  history: (
    skip: number = 0,
    limit: number = 10
  ): Promise<AxiosResponse<HistoryResponse>> =>
    client.get<HistoryResponse>('/api/v1/history', {
      params: { skip, limit },
    }),

  /**
   * Get aggregated risk statistics
   * GET /api/v1/stats
   *
   * @returns Promise<StatsResponse> containing total scans and risk distribution
   */
  stats: (): Promise<AxiosResponse<StatsResponse>> =>
    client.get<StatsResponse>('/api/v1/stats'),

  /**
   * Health check endpoint
   * GET /health
   *
   * @returns Promise<HealthResponse> with status information
   */
  health: (): Promise<AxiosResponse<HealthResponse>> =>
    client.get<HealthResponse>('/health'),
};

/**
 * ============================================================================
 * HELPER TYPES & CONVERSION FUNCTIONS
 * ============================================================================
 */

/**
 * ScanRecord - Simplified record type for table display
 * Used in components that show scan/history data
 * Unified interface that works with both CVEDetail and HistoryRecord
 */
export interface ScanRecord {
  cve_id: string;
  risk_level: string;
  risk_score: number | null; // Unified score field (risk_score from CVE, risk_score from history)
  analysis_summary: string;
  created_at: string | null; // ISO 8601 timestamp or null
}

/**
 * Convert a single CVEDetail to ScanRecord for table display
 *
 * @param cve - CVEDetail object from backend
 * @returns ScanRecord with essential fields for display
 */
export const convertCVEDetailToScanRecord = (cve: CVEDetail): ScanRecord => ({
  cve_id: cve.cve_id,
  risk_level: cve.risk_level,
  risk_score: cve.risk_score, // Use risk_score from CVEDetail
  analysis_summary: cve.analysis_summary,
  created_at: null, // CVEDetail doesn't have created_at
});

/**
 * Convert array of CVEDetail to ScanRecord array
 *
 * @param cves - Array of CVEDetail objects
 * @returns Array of ScanRecord objects
 */
export const convertCVEDetailsToScanRecords = (cves: CVEDetail[]): ScanRecord[] =>
  cves.map(convertCVEDetailToScanRecord);

/**
 * Convert HistoryRecord array to ScanRecord array
 *
 * @param records - Array of HistoryRecord objects
 * @returns Array of ScanRecord objects
 */
export const convertHistoryToScanRecords = (records: HistoryRecord[]): ScanRecord[] =>
  records.map((record) => ({
    cve_id: record.cve_id,
    risk_level: record.risk_level,
    risk_score: record.risk_score, // Map risk_score from history to risk_score for unified display
    analysis_summary: record.analysis_summary,
    created_at: record.created_at,
  }));

/**
 * ============================================================================
 * ERROR HANDLING UTILITIES
 * ============================================================================
 */

/**
 * Check if an API response contains valid data
 * Helps distinguish between successful empty responses and errors
 *
 * @param data - Response data
 * @returns true if data is valid and non-empty
 */
export const isValidQueryResponse = (data: QueryResponse): boolean => {
  return (
    data &&
    typeof data === 'object' &&
    Array.isArray(data.cve_list) &&
    data.cve_list.length > 0
  );
};

/**
 * Error code type for backend errors
 */
export type ErrorCode = 'RESOURCE_NOT_FOUND' | 'ANALYSIS_IN_PROGRESS' | 'EXTERNAL_SERVICE_ERROR' | 'INVALID_INPUT' | 'INTERNAL_ERROR';

/**
 * Extract error code from API response
 * Helps identify specific error types for specialized handling
 *
 * @param error - Error object
 * @returns Error code string or undefined if not found
 */
export const getErrorCode = (error: unknown): ErrorCode | undefined => {
  if (error instanceof Error) {
    if ('response' in error && error.response) {
      const response = error.response as any;
      return response.data?.error?.code as ErrorCode | undefined;
    }
  }
  return undefined;
};

/**
 * Extract error message from API response
 * Handles various error response formats and specific error codes
 *
 * @param error - Error object
 * @returns Friendly error message
 */
export const getErrorMessage = (error: unknown): string => {
  if (error instanceof Error) {
    // Axios error with response
    if ('response' in error && error.response) {
      const response = error.response as any;
      const errorCode = response.data?.error?.code as string | undefined;

      // Handle specific error codes
      if (errorCode === 'ANALYSIS_IN_PROGRESS') {
        return 'AI analysis is currently in progress for this package. Please check back in a few moments.';
      }

      if (response.data?.error?.message) {
        return response.data.error.message;
      }

      if (response.status === 202) {
        return 'Request accepted. Analysis is being processed. Please try again in a moment.';
      }
      if (response.status === 404) {
        return 'Resource not found. Please check your query and try again.';
      }
      if (response.status === 500) {
        return 'Server error. Please try again later.';
      }
    }
    return error.message || 'An unknown error occurred';
  }
  return 'An unknown error occurred';
};

/**
 * ============================================================================
 * API QUERY KEY FACTORIES
 * For use with react-query for consistent cache key management
 * ============================================================================
 */

/**
 * Query key factory for react-query
 * Ensures consistent cache key generation across the app
 */
export const queryKeys = {
  all: ['query'] as const,
  stats: () => [...queryKeys.all, 'stats'] as const,
  history: (skip?: number, limit?: number) =>
    [...queryKeys.all, 'history', skip, limit] as const,
  search: (query?: { package?: string; cve_id?: string }) =>
    [...queryKeys.all, 'search', query] as const,
  report: (cveId?: string) => [...queryKeys.all, 'report', cveId] as const,
  health: () => [...queryKeys.all, 'health'] as const,
};
