import React from 'react';
import { clsx } from 'clsx';

interface CardProps {
  children: React.ReactNode;
  className?: string;
  title?: string;
}

export const Card: React.FC<CardProps> = ({ children, className, title }) => {
  return (
    <div className={clsx('bg-white rounded-xl shadow-sm border border-slate-200/75', className)}>
      {title && (
        <div className="px-6 pt-6 pb-0">
          <h3 className="text-lg font-semibold text-slate-800 mb-6">{title}</h3>
        </div>
      )}
      <div className={title ? 'px-6 pb-6' : 'p-6'}>
        {children}
      </div>
    </div>
  );
};
