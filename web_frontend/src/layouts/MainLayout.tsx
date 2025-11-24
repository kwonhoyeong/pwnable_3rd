import React from 'react';
import { Outlet, Link, useLocation } from 'react-router-dom';
import { BarChart3, History, Shield, Bell, Search, User } from 'lucide-react';
import { clsx } from 'clsx';

export const MainLayout: React.FC = () => {
  const location = useLocation();

  const navigation = [
    { name: '분석', href: '/', icon: BarChart3 },
    { name: '히스토리', href: '/history', icon: History },
  ];

  const isActive = (path: string) => {
    if (path === '/') {
      return location.pathname === '/';
    }
    return location.pathname.startsWith(path);
  };

  return (
    <div className="min-h-screen bg-background font-sans text-white flex">
      {/* Fixed Sidebar */}
      <aside className="fixed top-0 left-0 h-screen w-[280px] bg-background flex flex-col z-50">
        {/* Logo Section */}
        <div className="p-8 flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-primary/20">
            <Shield className="w-6 h-6 text-primary" />
          </div>
          <h1 className="text-xl font-bold text-white tracking-tight">
            Dark Sentinel
          </h1>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-6 space-y-2 mt-4">
          <p className="px-4 text-xs font-semibold text-secondary uppercase tracking-wider mb-4">
            Menu
          </p>
          {navigation.map((item) => {
            const Icon = item.icon;
            const active = isActive(item.href);

            return (
              <Link
                key={item.name}
                to={item.href}
                className={clsx(
                  'flex items-center gap-4 px-4 py-4 rounded-2xl transition-all duration-200 font-medium',
                  active
                    ? 'bg-primary text-white shadow-lg shadow-primary/25'
                    : 'text-secondary hover:text-white hover:bg-surface'
                )}
              >
                <Icon className={clsx('w-5 h-5', active ? 'text-white' : 'text-secondary group-hover:text-white')} />
                <span>{item.name}</span>
              </Link>
            );
          })}
        </nav>

        {/* Sidebar Footer */}

      </aside>

      {/* Main Content Wrapper */}
      <div className="flex-1 ml-[280px] flex flex-col min-h-screen">


        {/* Main Content */}
        <main className="flex-1 p-10">
          <Outlet />
        </main>
      </div>
    </div>
  );
};
