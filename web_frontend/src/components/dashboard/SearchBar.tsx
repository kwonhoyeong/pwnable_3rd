import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../ui/Button';
import { Search, AlertCircle } from 'lucide-react';
import { clsx } from 'clsx';

export interface SearchBarProps {
  onSearch?: (packageName: string, version: string) => void;
  isLoading?: boolean;
  ecosystem?: string;
  onEcosystemChange?: (ecosystem: string) => void;
}

export const SearchBar: React.FC<SearchBarProps> = ({
  onSearch,
  isLoading = false,
  ecosystem = 'npm',
  onEcosystemChange
}) => {
  const [packageName, setPackageName] = useState('');
  const [version, setVersion] = useState('latest');
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!packageName.trim()) {
      setError('패키지 이름 또는 CVE ID를 입력하세요');
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
  };

  return (
    <div className="glass-panel p-6 mb-6 rounded-2xl">
      <form onSubmit={handleSearch} className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          {/* Ecosystem Selector */}
          <div className="md:col-span-1">
            <label
              htmlFor="ecosystem"
              className="block text-sm font-medium mb-2 text-sentinel-text-muted"
            >
              패키지
            </label>
            <select
              id="ecosystem"
              value={ecosystem}
              onChange={(e) => onEcosystemChange?.(e.target.value)}
              disabled={isLoading}
              className={clsx(
                'glass-input w-full px-4 py-2.5 rounded-lg appearance-none cursor-pointer',
                'disabled:opacity-50 disabled:cursor-not-allowed'
              )}
            >
              <option value="npm" className="bg-sentinel-surface text-white">NPM</option>
              <option value="pip" className="bg-sentinel-surface text-white">PIP</option>
              <option value="apt" className="bg-sentinel-surface text-white">APT</option>
            </select>
          </div>

          {/* Package Name Input */}
          <div className="md:col-span-2 relative">
            <label
              htmlFor="package"
              className="block text-sm font-medium mb-2 text-sentinel-text-muted"
            >
              패키지 이름
            </label>
            <div className="relative">
              <Search
                className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-sentinel-text-muted"
              />
              <input
                id="package"
                type="text"
                placeholder="예: react, lodash, CVE-2023-1234"
                value={packageName}
                onChange={(e) => {
                  setPackageName(e.target.value);
                  setError('');
                }}
                disabled={isLoading}
                className={clsx(
                  'glass-input w-full pl-11 pr-4 py-2.5 rounded-lg',
                  'disabled:opacity-50 disabled:cursor-not-allowed'
                )}
              />
            </div>
          </div>

          {/* Version Input */}
          <div className="md:col-span-1">
            <label
              htmlFor="version"
              className="block text-sm font-medium mb-2 text-sentinel-text-muted"
            >
              버전
            </label>
            <input
              id="version"
              type="text"
              placeholder="latest"
              value={version}
              onChange={(e) => setVersion(e.target.value)}
              disabled={isLoading}
              className={clsx(
                'glass-input w-full px-4 py-2.5 rounded-lg',
                'disabled:opacity-50 disabled:cursor-not-allowed'
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
              className="w-full btn-primary"
            >
              {isLoading ? '분석 중...' : '분석'}
            </Button>
          </div>
        </div>

        {/* Error Message */}
        {error && (
          <div className="flex items-center gap-2 p-3 rounded-lg border bg-sentinel-error/10 border-sentinel-error/30 text-sentinel-error">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <p className="text-sm">{error}</p>
          </div>
        )}
      </form>
    </div>
  );
};
