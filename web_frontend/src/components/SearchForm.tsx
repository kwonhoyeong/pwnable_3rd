import React, { useState } from 'react';
import { useQueryState } from '../store/queryContext';
import { Search, Package, ArrowRight, Loader2 } from 'lucide-react';

export const SearchForm: React.FC = () => {
  const { search, loading } = useQueryState();
  const [pkgName, setPkgName] = useState('');
  const [ecosystem, setEcosystem] = useState('npm');

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    // Updated search call to use pkgName and ecosystem
    // Note: Assuming search function accepts package and ecosystem. 
    // If not, we might need to adjust the arguments or update the context.
    // For now, passing package as the main argument.
    await search({ package: pkgName, ecosystem });
  };

  return (
    <form onSubmit={handleSubmit} className="w-full max-w-3xl mx-auto">
      <div className="glass-panel p-8 rounded-2xl relative overflow-hidden group">
        {/* Background Glow */}
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full h-1 bg-gradient-to-r from-transparent via-sentinel-primary to-transparent opacity-50 group-hover:opacity-100 transition-opacity duration-500"></div>

        <div className="flex flex-col md:flex-row gap-4 relative z-10">
          <div className="flex-1 relative">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-sentinel-text-muted group-focus-within:text-sentinel-primary transition-colors" />
            <input
              type="text"
              value={pkgName}
              onChange={(e) => setPkgName(e.target.value)}
              placeholder="Enter package name (e.g., react, axios)..."
              className="glass-input w-full pl-12 pr-4 py-4 rounded-xl text-lg"
              required
            />
          </div>

          <div className="w-full md:w-48 relative">
            <Package className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-sentinel-text-muted" />
            <select
              value={ecosystem}
              onChange={(e) => setEcosystem(e.target.value)}
              className="glass-input w-full pl-12 pr-10 py-4 rounded-xl text-lg appearance-none cursor-pointer"
            >
              <option value="npm" className="bg-sentinel-surface text-white">NPM</option>
              <option value="pypi" className="bg-sentinel-surface text-white">PyPI</option>
              <option value="apt" className="bg-sentinel-surface text-white">APT</option>
            </select>
            <div className="absolute right-4 top-1/2 -translate-y-1/2 pointer-events-none">
              <svg className="w-4 h-4 text-sentinel-text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7"></path></svg>
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="btn-primary px-8 py-4 rounded-xl flex items-center justify-center gap-2 min-w-[140px] disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <>
                <span>ANALYZE</span>
                <ArrowRight className="w-5 h-5" />
              </>
            )}
          </button>
        </div>
      </div>
    </form>
  );
};
