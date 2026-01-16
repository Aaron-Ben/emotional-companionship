/** Floating Action Button component */

import React from 'react';

interface FloatingActionButtonProps {
  onClick: () => void;
  icon: React.ReactNode;
  ariaLabel: string;
  position?: 'top-left' | 'top-right' | 'bottom-left' | 'bottom-right';
}

export const FloatingActionButton: React.FC<FloatingActionButtonProps> = ({
  onClick,
  icon,
  ariaLabel,
  position = 'bottom-right',
}) => {
  const positionClasses: Record<typeof position, string> = {
    'top-left': 'top-4 left-4',
    'top-right': 'top-4 right-4',
    'bottom-left': 'bottom-4 left-4',
    'bottom-right': 'bottom-4 right-4',
  };

  return (
    <button
      className={`fab ${positionClasses[position]}`}
      onClick={onClick}
      aria-label={ariaLabel}
      title={ariaLabel}
    >
      {icon}
    </button>
  );
};
