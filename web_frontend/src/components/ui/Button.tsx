import React from 'react';
import { clsx } from 'clsx';
import { Loader2 } from 'lucide-react';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
  children: React.ReactNode;
}

export const Button: React.FC<ButtonProps> = ({
  variant = 'primary',
  size = 'md',
  isLoading = false,
  className,
  children,
  disabled,
  ...props
}) => {
  const baseClasses = 'font-medium transition-all duration-150 rounded inline-flex items-center justify-center gap-2 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-black';

  const variantClasses = {
    primary: 'btn-primary',
    secondary: 'btn-secondary',
    danger: clsx(
      'px-5 py-2.5 rounded font-medium',
      'transition-all duration-150',
      'disabled:opacity-50 disabled:cursor-not-allowed'
    ),
  };

  const sizeClasses = {
    sm: 'px-3 py-1.5 text-xs',
    md: 'text-sm',
    lg: 'px-6 py-3 text-base',
  };

  const dangerStyle = variant === 'danger' ? {
    backgroundColor: 'var(--color-critical)',
    color: 'white',
  } : undefined;

  const isDisabled = disabled || isLoading;

  return (
    <button
      className={clsx(baseClasses, variantClasses[variant], sizeClasses[size], className)}
      style={dangerStyle}
      disabled={isDisabled}
      {...props}
    >
      {isLoading && <Loader2 className="w-4 h-4 animate-spin" />}
      <span>{children}</span>
    </button>
  );
};
