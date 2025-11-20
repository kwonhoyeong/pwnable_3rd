import client from './client';

export const queryAPI = {
  query: (params: { package?: string; cve_id?: string }) =>
    client.get('/api/v1/query', { params }),

  history: (skip: number = 0, limit: number = 10) =>
    client.get('/api/v1/history', { params: { skip, limit } }),

  stats: () => client.get('/api/v1/stats'),

  health: () => client.get('/health'),
};

export type QueryResponse = {
  cve_id: string;
  epss_score?: number;
  cvss_score?: number;
  risk_level: string;
  analysis_summary: string;
  recommendations: string[];
};

export type HistoryRecord = {
  cve_id: string;
  risk_level: string;
  risk_score?: number;
  analysis_summary: string;
  recommendations: string[];
  generated_at?: string;
  created_at?: string;
};

export type StatsResponse = {
  total_scans: number;
  risk_distribution: {
    CRITICAL: number;
    HIGH: number;
    MEDIUM: number;
    LOW: number;
    Unknown: number;
  };
};
