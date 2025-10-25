import React, { createContext, useContext, useState } from 'react';
import axios from 'axios';

export interface CVEDetail {
  cve_id: string;
  epss_score: number;
  risk_level: string;
  analysis_summary: string;
  recommendations: string[];
}

export interface QueryState {
  loading: boolean;
  error: string | null;
  package?: string;
  cve_id?: string;
  results: CVEDetail[];
}

interface QueryContextValue extends QueryState {
  search: (params: { package?: string; cve_id?: string }) => Promise<void>;
}

const QueryContext = createContext<QueryContextValue | undefined>(undefined);

export const QueryProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [state, setState] = useState<QueryState>({ loading: false, error: null, results: [] });

  const search = async ({ package: pkg, cve_id }: { package?: string; cve_id?: string }) => {
    setState((prev) => ({ ...prev, loading: true, error: null }));
    try {
      const response = await axios.get('/api/v1/query', { params: { package: pkg, cve_id } });
      setState({
        loading: false,
        error: null,
        package: response.data.package,
        cve_id: response.data.cve_id,
        results: response.data.cve_list || [],
      });
    } catch (error) {
      setState({ loading: false, error: '조회 실패(Query failed)', results: [], package: pkg, cve_id });
    }
  };

  return (
    <QueryContext.Provider value={{ ...state, search }}>
      {children}
    </QueryContext.Provider>
  );
};

export const useQueryState = (): QueryContextValue => {
  const context = useContext(QueryContext);
  if (!context) {
    throw new Error('useQueryState must be used within QueryProvider');
  }
  return context;
};

