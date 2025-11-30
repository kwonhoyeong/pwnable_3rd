import React from 'react';
import { Link, useLocation, Outlet } from 'react-router-dom';
import { Shield, LayoutDashboard, Clock, Activity, Menu, Bell } from 'lucide-react';

const MainLayout: React.FC = () => {
  const location = useLocation();

  const isActive = (path: string) => {
    return location.pathname === path ? 'text-sentinel-primary bg-sentinel-primary/10 border-r-2 border-sentinel-primary' : 'text-sentinel-text-muted hover:text-white hover:bg-white/5';
  };

  return (
    <div className="flex min-h-screen bg-sentinel-bg text-sentinel-text-main font-sans selection:bg-sentinel-primary/30">
      {/* Sidebar */}
      <aside className="fixed left-0 top-0 h-full w-64 glass-panel border-r border-white/10 z-50 hidden md:flex flex-col">
        <div className="p-6 flex items-center gap-3 border-b border-white/10">
          <div className="relative">
            <Shield className="w-8 h-8 text-sentinel-primary" />
            <div className="absolute inset-0 bg-sentinel-primary/20 blur-lg rounded-full animate-pulse"></div>
          </div>
          <div>
            <h1 className="font-heading font-bold text-xl tracking-wider text-white">SENTINEL</h1>
            <p className="text-xs text-sentinel-primary tracking-widest uppercase">Threat Intel</p>
          </div>
        </div>

        <nav className="flex-1 py-6 flex flex-col gap-2">
          <Link to="/" className={`flex items-center gap-3 px-6 py-3 transition-all duration-300 ${isActive('/')}`}>
            <LayoutDashboard className="w-5 h-5" />
            <span className="font-medium tracking-wide">Dashboard</span>
          </Link>
          <Link to="/history" className={`flex items-center gap-3 px-6 py-3 transition-all duration-300 ${isActive('/history')}`}>
            <Clock className="w-5 h-5" />
            <span className="font-medium tracking-wide">Scan History</span>
          </Link>
          <div className="px-6 py-3 mt-4">
            <p className="text-xs font-bold text-sentinel-text-muted uppercase tracking-wider mb-2">System</p>
            <div className="flex items-center gap-3 text-sentinel-text-muted px-2 py-1">
              <Activity className="w-4 h-4 text-sentinel-success" />
              <span className="text-sm">Operational</span>
            </div>
          </div>
        </nav>

        {/* Sidebar Footer */}

      </aside>

      {/* Main Content Wrapper */}
      <div className="flex-1 ml-[280px] flex flex-col min-h-screen">


        {/* Main Content */}
        <div className="p-6 md:p-8 max-w-7xl mx-auto w-full animate-fade-in">
          <Outlet />
        </div>
      </div>
    </div>
  );
};

export { MainLayout };
