/** Loading spinner component */

import React from 'react';

export const LoadingSpinner: React.FC<{ size?: 'small' | 'medium' | 'large' }> = ({
  size = 'medium'
}) => {
  const sizeClasses = {
    small: 'w-6 h-6',
    medium: 'w-10 h-10',
    large: 'w-16 h-16',
  };

  return (
    <div className="flex items-center justify-center">
      <div className={`loading-spinner ${sizeClasses[size]}`} />
    </div>
  );
};
