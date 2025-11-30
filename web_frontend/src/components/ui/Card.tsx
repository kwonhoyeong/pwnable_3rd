import React from 'react';
import { clsx } from 'clsx';

interface CardProps {
  children: React.ReactNode;
  className?: string;
  title?: string;
}

export const Card: React.FC<CardProps> = ({ children, className, title }) => {
  return (
    <div
      className={clsx('glass-panel p-6 rounded-2xl', className)}
    >
      {title && (
        <div className="mb-6">
          <h3 className="text-lg font-semibold text-white">
            {title}
          </h3>
        </div>
      )}
      <div>
        {children}
      </div>
    </div>
  );
};
