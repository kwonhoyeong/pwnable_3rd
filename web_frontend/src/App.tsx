import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { QueryClientProvider, QueryClient } from '@tanstack/react-query';
import { MainLayout } from './layouts/MainLayout';
import { Dashboard } from './pages/Dashboard';
import { History } from './pages/History';
import { ReportDetail } from './pages/ReportDetail';

const queryClient = new QueryClient();

const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <Routes>
          <Route element={<MainLayout />}>
            <Route index element={<Dashboard />} />
            <Route path="/history" element={<History />} />
            <Route path="/report/:cveId" element={<ReportDetail />} />
          </Route>
        </Routes>
      </Router>
    </QueryClientProvider>
  );
};

export default App;

