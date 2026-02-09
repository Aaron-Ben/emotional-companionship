/** Individual topic card component - Refined elegant style */

import React from 'react';
import { clsx } from 'clsx';
import type { TopicListItem } from '../../types/chat';

interface TopicCardProps {
  topic: TopicListItem;
  isActive: boolean;
  onClick: () => void;
  onDelete: (e: React.MouseEvent) => void;
}

export const TopicCard: React.FC<TopicCardProps> = ({
  topic,
  isActive,
  onClick,
  onDelete,
}) => {
  const previewText =
    topic.preview && topic.preview.length > 40
      ? `${topic.preview.slice(0, 40)}...`
      : topic.preview || '新对话...';

  return (
    <div
      className={clsx(
        'group p-4 mb-2 bg-white dark:bg-neutral-800 rounded-2xl border cursor-pointer transition-all duration-200',
        isActive
          ? 'border-rose-300 dark:border-rose-600 shadow-sm'
          : 'border-neutral-200 dark:border-neutral-700 hover:border-rose-200 dark:hover:border-rose-700 hover:shadow-sm'
      )}
      onClick={onClick}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div
            className={clsx(
              'text-sm leading-relaxed mb-2 break-words',
              isActive
                ? 'text-neutral-800 dark:text-neutral-100 font-medium'
                : 'text-neutral-600 dark:text-neutral-400'
            )}
          >
            {previewText}
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-neutral-400 dark:text-neutral-500">
              {topic.timeAgo}
            </span>
            {topic.topic.message_count > 0 && (
              <span className="inline-flex items-center px-2 py-0.5 bg-rose-100 dark:bg-rose-900/30 text-rose-600 dark:text-rose-400 text-xs font-medium rounded-full">
                {topic.topic.message_count}
              </span>
            )}
          </div>
        </div>
        <button
          className="w-6 h-6 flex items-center justify-center rounded-full text-neutral-300 hover:text-rose-500 hover:bg-rose-50 dark:hover:bg-rose-950/20 transition-all opacity-0 group-hover:opacity-100 flex-shrink-0"
          onClick={onDelete}
          aria-label="删除对话"
          title="删除对话"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M18 6L6 18M6 6l12 12"/>
          </svg>
        </button>
      </div>
    </div>
  );
};
