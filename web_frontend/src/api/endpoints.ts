import client from './client';

/**
 * ============================================================================
 * TYPE DEFINITIONS - Match backend models from query_api/app/models.py
 * ============================================================================
 */

/**
 * CVEDetail - Detailed information about a single CVE
 * Matches backend CVEDetail model
 */
export interface CVEDetail {
  cve_id: string;
  epss_score: number | null;
  cvss_score: number | null;
  risk_level: string; // "CRITICAL", "HIGH", "MEDIUM", "LOW", "Unknown"
  analysis_summary: string; // Markdown formatted
  recommendations: string[];
  priority_score: number; // Float 0.0-10.0
  priority_label: string; // "CRITICAL", "HIGH", etc.
  created_at?: string; // ISO timestamp
}

/**
 * QueryResponse - Response from /api/v1/query endpoint
 * Wraps a list of CVEDetail objects
 */
export interface QueryResponse {
  package?: string;
  cve_id?: string;
  cve_list: CVEDetail[];
}

/**
 * HistoryResponse - Response from /api/v1/history endpoint
 * Paginated list of historical CVE scans
 */
export interface HistoryResponse {
  records: CVEDetail[];
  skip: number;
  limit: number;
  total: number;
}

/**
 * StatsResponse - Response from /api/v1/stats endpoint
 * Aggregated statistics about scanned vulnerabilities
 */
export interface StatsResponse {
  total_scans: number;
  risk_distribution: {
    CRITICAL: number;
    HIGH: number;
    MEDIUM: number;
    LOW: number;
    Unknown: number;
  };
}

/**
 * HealthResponse - Response from /health endpoint
 */
export interface HealthResponse {
  status: string;
  timestamp: string;
}

/**
 * ============================================================================
 * API ENDPOINTS
 * ============================================================================
 */

export const queryAPI = {
  /**
   * Search for vulnerabilities by CVE ID
   * GET /api/v1/query?cve_id={cveId}
   */
  searchByCVE: (cveId: string) =>
    client.get<QueryResponse>('/api/v1/query', { params: { cve_id: cveId } }),

  /**
   * Search for vulnerabilities by package name
   * GET /api/v1/query?package={packageName}
   */
  searchByPackage: (packageName: string) =>
    client.get<QueryResponse>('/api/v1/query', { params: { package: packageName } }),

  /**
   * Generic query endpoint - supports both package and CVE ID search
   * GET /api/v1/query?package={packageName}&cve_id={cveId}
   */
  query: (params: { package?: string; cve_id?: string }) =>
    client.get<QueryResponse>('/api/v1/query', { params }),

  /**
   * Get paginated analysis history
   * GET /api/v1/history?skip={skip}&limit={limit}
   */
  history: (skip: number = 0, limit: number = 10) =>
    client.get<HistoryResponse>('/api/v1/history', { params: { skip, limit } }),

  /**
   * Get aggregated risk statistics
   * GET /api/v1/stats
   */
  stats: () => client.get<StatsResponse>('/api/v1/stats'),

  /**
   * Health check endpoint
   * GET /health
   */
  health: () => client.get<HealthResponse>('/health'),
};

/**
 * ============================================================================
 * HELPER TYPES FOR COMPONENTS
 * ============================================================================
 */

/**
 * ScanRecord - Simplified record for display in tables
 * Used in DashboardPage and History page
 */
export interface ScanRecord {
  cve_id: string;
  risk_level: string;
  risk_score?: number; // priority_score from backend
  analysis_summary: string;
  created_at?: string;
}

/**
 * Convert CVEDetail to ScanRecord for table display
 */
export const convertCVEDetailToScanRecord = (cve: CVEDetail): ScanRecord => ({
  cve_id: cve.cve_id,
  risk_level: cve.risk_level,
  risk_score: cve.priority_score,
  analysis_summary: cve.analysis_summary,
  created_at: cve.created_at,
});

/**
 * Convert array of CVEDetail to ScanRecord array
 */
export const convertCVEDetailsToScanRecords = (cves: CVEDetail[]): ScanRecord[] =>
  cves.map(convertCVEDetailToScanRecord);
