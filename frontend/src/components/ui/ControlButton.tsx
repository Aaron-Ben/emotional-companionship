/** Control Button Component - Unified style for toggle buttons */

import React from 'react';
import { clsx } from 'clsx';

interface ControlButtonProps {
  icon: React.ReactNode | null;
  label: string;
  onClick: () => void;
  className?: string;
  title?: string;
}

export const ControlButton: React.FC<ControlButtonProps> = ({
  icon,
  label,
  onClick,
  className = '',
  title,
}) => {
  return (
    <button
      onClick={onClick}
      className={clsx(
        'flex items-center gap-2 px-4 py-2.5 rounded-full text-sm font-semibold cursor-pointer transition-all duration-300',
        'border-2 shadow-lg hover:-translate-y-0.5 hover:shadow-xl active:translate-y-0',
        'bg-gradient-to-r from-pink-300 to-pink-500 border-pink-200 text-white shadow-pink-300/30 hover:from-pink-500 hover:to-pink-600 hover:shadow-pink-400/40',
        className
      )}
      title={title}
      type="button"
    >
      {icon && <span className="text-lg">{icon}</span>}
      <span className="text-[13px] font-semibold hidden md:inline">{label}</span>
    </button>
  );
};
