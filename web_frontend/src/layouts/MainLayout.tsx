import React from 'react';
import { Link, Outlet, useLocation } from 'react-router-dom';
import { clsx } from 'clsx';
import { BarChart3, History, Settings } from 'lucide-react';

export const MainLayout: React.FC = () => {
  const location = useLocation();

  const navItems = [
    { path: '/', label: 'Dashboard', icon: BarChart3 },
    { path: '/history', label: 'History', icon: History },
  ];

  return (
    <div className="min-h-screen flex flex-col bg-slate-50">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-blue-600 rounded-lg flex items-center justify-center">
              <BarChart3 className="w-6 h-6 text-white" />
            </div>
            <h1 className="text-2xl font-bold text-slate-900">Threat Intelligence</h1>
          </div>
          <Settings className="w-5 h-5 text-slate-600 cursor-pointer hover:text-slate-900" />
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar Navigation */}
        <nav className="w-64 bg-white border-r border-slate-200 overflow-y-auto">
          <div className="p-4 space-y-2">
            {navItems.map(({ path, label, icon: Icon }) => (
              <Link
                key={path}
                to={path}
                className={clsx(
                  'flex items-center gap-3 px-4 py-3 rounded-lg transition-colors',
                  location.pathname === path
                    ? 'bg-blue-50 text-blue-600 font-medium'
                    : 'text-slate-700 hover:bg-slate-50'
                )}
              >
                <Icon className="w-5 h-5" />
                <span>{label}</span>
              </Link>
            ))}
          </div>
        </nav>

        {/* Main Content */}
        <main className="flex-1 overflow-y-auto p-8">
          <div className="max-w-7xl">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
};
