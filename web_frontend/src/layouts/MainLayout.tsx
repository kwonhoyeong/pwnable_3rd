import React from 'react';
import { NavLink, Outlet, useLocation } from 'react-router-dom';
import { clsx } from 'clsx';
import { LayoutDashboard, History, Shield } from 'lucide-react';

export const MainLayout: React.FC = () => {
  const location = useLocation();

  // Get page title from route
  const getPageTitle = () => {
    switch (location.pathname) {
      case '/':
        return 'Dashboard';
      case '/history':
        return 'Analysis History';
      case '/report':
        return 'Threat Report';
      default:
        if (location.pathname.startsWith('/report/')) {
          const cveId = location.pathname.split('/').pop();
          return `Report: ${cveId}`;
        }
        return 'NPM Threat Sentry';
    }
  };

  const navItems = [
    { path: '/', label: 'Dashboard', icon: LayoutDashboard },
    { path: '/history', label: 'History', icon: History },
  ];

  return (
    <div className="min-h-screen flex bg-slate-50">
      {/* Fixed Dark Sidebar */}
      <aside className="w-64 bg-slate-900 text-white flex flex-col border-r border-slate-800 fixed h-screen overflow-y-auto">
        {/* Logo/Brand Section */}
        <div className="p-6 border-b border-slate-800 flex items-center gap-3">
          <div className="w-10 h-10 bg-blue-600 rounded-lg flex items-center justify-center flex-shrink-0">
            <Shield className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-lg font-bold leading-tight">NPM Threat Sentry</h1>
            <p className="text-xs text-slate-400">Vulnerability Assessment</p>
          </div>
        </div>

        {/* Navigation Links */}
        <nav className="flex-1 px-3 py-6 space-y-2">
          {navItems.map(({ path, label, icon: Icon }) => (
            <NavLink
              key={path}
              to={path}
              className={({ isActive }) =>
                clsx(
                  'flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-200 font-medium',
                  isActive
                    ? 'bg-slate-800 text-white border-l-4 border-blue-500'
                    : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                )
              }
            >
              {({ isActive }) => (
                <>
                  <Icon className={clsx('w-5 h-5', isActive && 'text-blue-400')} />
                  <span>{label}</span>
                </>
              )}
            </NavLink>
          ))}
        </nav>

        {/* Sidebar Footer */}
        <div className="p-4 border-t border-slate-800 text-xs text-slate-400">
          <p className="font-semibold">v1.0.0</p>
          <p className="mt-2 text-slate-500">Enterprise Threat Intelligence</p>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 ml-64 flex flex-col h-screen overflow-hidden">
        {/* Header */}
        <header className="h-16 bg-white border-b border-slate-200 shadow-sm flex items-center justify-between px-8 sticky top-0 z-10">
          <div>
            <h2 className="text-xl font-bold text-slate-900">{getPageTitle()}</h2>
            <p className="text-sm text-slate-500">Comprehensive vulnerability analysis</p>
          </div>
          <div className="flex items-center gap-4">
            <div className="w-10 h-10 bg-slate-200 rounded-full flex items-center justify-center">
              <span className="text-sm font-medium text-slate-700">U</span>
            </div>
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 overflow-y-auto bg-slate-50 p-8">
          <div className="max-w-7xl mx-auto">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
};
