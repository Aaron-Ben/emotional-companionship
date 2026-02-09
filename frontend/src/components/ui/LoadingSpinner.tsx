/** Loading spinner component - Refined elegant style */

import React from 'react';

export const LoadingSpinner: React.FC<{ size?: 'small' | 'medium' | 'large' }> = ({
  size = 'medium'
}) => {
  const sizeClasses = {
    small: 'w-6 h-6 border-2',
    medium: 'w-10 h-10 border-3',
    large: 'w-16 h-16 border-4',
  };

  return (
    <div className="flex items-center justify-center">
      <div
        className={clsx(
          sizeClasses[size],
          'rounded-full border-rose-200 border-t-rose-500 animate-spin'
        )}
      />
    </div>
  );
};

function clsx(...classes: (string | boolean | undefined | null)[]) {
  return classes.filter(Boolean).join(' ');
}
