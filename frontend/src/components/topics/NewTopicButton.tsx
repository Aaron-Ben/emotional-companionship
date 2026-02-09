/** New topic button component - Refined elegant style */

import React from 'react';
import { clsx } from 'clsx';

interface NewTopicButtonProps {
  onClick: () => void;
  disabled?: boolean;
  loading?: boolean;
}

export const NewTopicButton: React.FC<NewTopicButtonProps> = ({
  onClick,
  disabled = false,
  loading = false,
}) => {
  return (
    <button
      className={clsx(
        'w-full px-5 py-3 border-2 border-dashed rounded-2xl font-medium cursor-pointer transition-all duration-200 flex items-center justify-center gap-2 active:scale-[0.98]',
        'border-rose-300 dark:border-rose-700 bg-gradient-to-br from-rose-50/50 to-transparent dark:from-rose-950/20 text-rose-600 dark:text-rose-400',
        'hover:border-rose-400 dark:hover:border-rose-500 hover:bg-gradient-to-br hover:from-rose-100 hover:to-transparent dark:hover:from-rose-950/30 hover:shadow-sm',
        'disabled:opacity-50 disabled:cursor-not-allowed'
      )}
      onClick={onClick}
      disabled={disabled || loading}
      aria-label="新对话"
      title="开始新对话"
    >
      {loading ? (
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 border-2 border-rose-300 border-t-rose-500 rounded-full animate-spin"></div>
          <span className="text-sm">创建中...</span>
        </div>
      ) : (
        <>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" className="shrink-0">
            <path d="M12 5v14M5 12h14"/>
          </svg>
          <span className="text-sm">新对话</span>
        </>
      )}
    </button>
  );
};
