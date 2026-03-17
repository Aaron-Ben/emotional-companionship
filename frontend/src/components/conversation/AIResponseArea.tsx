/** AI Response Area Component - Refined elegant style */

import React from 'react';

interface AIResponseAreaProps {
  content: string;
  isStreaming: boolean;
  visible: boolean;
}

export const AIResponseArea: React.FC<AIResponseAreaProps> = ({
  content,
  isStreaming,
  visible,
}) => {
  if (!visible) return null;

  return (
    <div className="px-6 pb-6">
      <div className="flex items-center justify-between gap-2 mb-3">
        <label className="text-sm font-medium text-rose-500 dark:text-rose-400">
          妹妹的回复
        </label>
      </div>
      <div className="bg-gradient-to-br from-rose-50/50 to-transparent dark:from-rose-950/20 border-2 border-rose-100 dark:border-rose-900/30 rounded-2xl p-5 min-h-[60px]">
        {isStreaming && !content ? (
          <div className="flex items-center gap-1.5 h-10">
            <span className="w-2 h-2 rounded-full bg-rose-400 dark:bg-rose-500 animate-typing"></span>
            <span className="w-2 h-2 rounded-full bg-rose-400 dark:bg-rose-500 animate-typing delay-150"></span>
            <span className="w-2 h-2 rounded-full bg-rose-400 dark:bg-rose-500 animate-typing delay-225"></span>
          </div>
        ) : (
          <div className="text-base leading-relaxed text-neutral-700 dark:text-neutral-300 whitespace-pre-wrap">
            {content || (isStreaming ? '正在思考...' : '')}
          </div>
        )}
      </div>
    </div>
  );
};
