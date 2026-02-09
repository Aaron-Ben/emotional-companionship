/** Typing indicator component for showing when character is "thinking" - Refined elegant style */

import React from 'react';

export const TypingIndicator: React.FC = () => {
  return (
    <div className="bg-white dark:bg-neutral-800 rounded-2xl rounded-bl-sm px-5 py-3 shadow-sm border border-neutral-200 dark:border-neutral-700">
      <div className="flex gap-1.5 items-center">
        <span className="w-2 h-2 rounded-full bg-rose-400 dark:bg-rose-500 animate-typing"></span>
        <span className="w-2 h-2 rounded-full bg-rose-400 dark:bg-rose-500 animate-typing delay-150"></span>
        <span className="w-2 h-2 rounded-full bg-rose-400 dark:bg-rose-500 animate-typing delay-225"></span>
      </div>
    </div>
  );
};
