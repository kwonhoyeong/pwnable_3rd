import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../ui/Button';
import { Search, AlertCircle } from 'lucide-react';
import { clsx } from 'clsx';

export interface SearchBarProps {
  onSearch?: (packageName: string, version: string) => void;
  isLoading?: boolean;
}

export const SearchBar: React.FC<SearchBarProps> = ({ onSearch, isLoading = false }) => {
  const [packageName, setPackageName] = useState('');
  const [version, setVersion] = useState('latest');
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!packageName.trim()) {
      setError('Please enter a package name or CVE ID');
      return;
    }

    const trimmedQuery = packageName.trim();

    // Check if it's a CVE ID
    if (trimmedQuery.match(/^CVE-\d{4}-\d+$/i)) {
      navigate(`/report/${trimmedQuery}`);
    } else {
      // It's a package search
      if (onSearch) {
        onSearch(trimmedQuery, version);
      } else {
        console.log('Searching for package:', trimmedQuery, 'version:', version);
      }
    }

    // Don't clear the fields - user might want to refine search
  };

  return (
    <div className="mb-8">
      <form onSubmit={handleSearch} className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {/* Package Name Input */}
          <div className="md:col-span-2 relative">
            <label htmlFor="package" className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
              Package Name
            </label>
            <div className="relative">
              <Search className="absolute left-3 top-3 w-5 h-5 text-slate-400 dark:text-slate-500" />
              <input
                id="package"
                type="text"
                placeholder="e.g., react, lodash, or CVE-2023-1234"
                value={packageName}
                onChange={(e) => {
                  setPackageName(e.target.value);
                  setError('');
                }}
                disabled={isLoading}
                className={clsx(
                  'w-full pl-10 pr-4 py-2',
                  'border border-slate-300 dark:border-slate-600',
                  'bg-white dark:bg-slate-800',
                  'text-slate-900 dark:text-white',
                  'rounded-lg',
                  'focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400',
                  'disabled:bg-slate-50 dark:disabled:bg-slate-900 disabled:cursor-not-allowed',
                  'placeholder:text-slate-500 dark:placeholder:text-slate-400'
                )}
              />
            </div>
          </div>

          {/* Version Input */}
          <div className="md:col-span-1">
            <label htmlFor="version" className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
              Version
            </label>
            <input
              id="version"
              type="text"
              placeholder="e.g., 1.0.0"
              value={version}
              onChange={(e) => setVersion(e.target.value)}
              disabled={isLoading}
              className={clsx(
                'w-full px-4 py-2',
                'border border-slate-300 dark:border-slate-600',
                'bg-white dark:bg-slate-800',
                'text-slate-900 dark:text-white',
                'rounded-lg',
                'focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400',
                'disabled:bg-slate-50 dark:disabled:bg-slate-900 disabled:cursor-not-allowed',
                'placeholder:text-slate-500 dark:placeholder:text-slate-400'
              )}
            />
          </div>

          {/* Search Button */}
          <div className="md:col-span-1 flex items-end">
            <Button
              type="submit"
              variant="primary"
              disabled={isLoading || !packageName.trim()}
              isLoading={isLoading}
              className="w-full"
            >
              {isLoading ? 'Analyzing...' : 'Analyze'}
            </Button>
          </div>
        </div>

        {/* Error Message */}
        {error && (
          <div className="flex items-center gap-2 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-800 dark:text-red-200">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <p className="text-sm">{error}</p>
          </div>
        )}
      </form>
    </div>
  );
};
