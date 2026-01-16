/** Anime-style button component */

import React from 'react';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary';
  children: React.ReactNode;
}

export const Button: React.FC<ButtonProps> = ({
  variant = 'primary',
  children,
  className = '',
  ...props
}) => {
  const baseClasses = 'anime-btn';
  const variantClasses = variant === 'secondary' ? 'anime-btn-secondary' : '';

  return (
    <button
      className={`${baseClasses} ${variantClasses} ${className}`.trim()}
      {...props}
    >
      <span className="relative z-10">{children}</span>
    </button>
  );
};
