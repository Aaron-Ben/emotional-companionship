/** Floating Action Button component - Refined elegant style */

import React from 'react';
import { clsx } from 'clsx';

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
      className={clsx(
        'fixed w-14 h-14 rounded-full bg-gradient-to-br from-rose-400 to-rose-500 text-white shadow-lg hover:shadow-xl transition-all duration-200 flex items-center justify-center z-40 hover:scale-105 active:scale-[0.98]',
        'hover:from-rose-500 hover:to-rose-600'
      )}
      style={getPositionStyle(position, index)}
      onClick={onClick}
      aria-label={ariaLabel}
      title={ariaLabel}
    >
      {icon}
    </button>
  );
};
