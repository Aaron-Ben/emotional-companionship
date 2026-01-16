/** Floating Action Button component */

import React from 'react';

interface FloatingActionButtonProps {
  onClick: () => void;
  icon: React.ReactNode;
  ariaLabel: string;
  position?: 'top-left' | 'top-right' | 'bottom-left' | 'bottom-right';
  index?: number; // For spacing multiple buttons
}

export const FloatingActionButton: React.FC<FloatingActionButtonProps> = ({
  onClick,
  icon,
  ariaLabel,
  position = 'bottom-right',
  index = 0,
}) => {
  const getPositionStyle = (pos: typeof position, idx: number) => {
    const baseSpacing = 16; // 1rem
    const buttonSpacing = 64; // 56px button + 8px gap
    const spacing = baseSpacing + (idx * buttonSpacing);

    switch (pos) {
      case 'top-left':
        return { top: '1rem', left: '1rem' };
      case 'top-right':
        return { top: '1rem', right: '1rem' };
      case 'bottom-left':
        return { bottom: `${spacing}px`, left: '1rem' };
      case 'bottom-right':
        return { bottom: `${spacing}px`, right: '1rem' };
      default:
        return { bottom: '1rem', right: '1rem' };
    }
  };

  return (
    <button
      className="fab"
      style={getPositionStyle(position, index)}
      onClick={onClick}
      aria-label={ariaLabel}
      title={ariaLabel}
    >
      {icon}
    </button>
  );
};
