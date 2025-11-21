import React from 'react';

export const HistoryPage: React.FC = () => {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-slate-900">Analysis History</h1>
        <p className="text-slate-600 mt-2">View your previous vulnerability scans</p>
      </div>

      <div className="bg-white rounded-lg shadow-sm border border-slate-200 p-6">
        <h2 className="text-lg font-semibold text-slate-900 mb-4">History Content</h2>
        <p className="text-slate-600">History page is loading. Coming soon with paginated scan history.</p>
      </div>
    </div>
  );
};
