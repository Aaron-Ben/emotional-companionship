/** Topic sidebar component - Refined elegant style */

import React, { useState } from 'react';
import type { TopicListItem } from '../../types/chat';
import { TopicCard } from './TopicCard';
import { NewTopicButton } from './NewTopicButton';
import { clsx } from 'clsx';

interface TopicSidebarProps {
  topics: TopicListItem[];
  currentTopicId: number | null;
  loading: boolean;
  collapsed: boolean;
  onSelectTopic: (topicId: number) => void;
  onCreateTopic: () => void;
  onDeleteTopic: (topicId: number) => void;
  onToggleCollapse: () => void;
}

export const TopicSidebar: React.FC<TopicSidebarProps> = ({
  topics,
  currentTopicId,
  loading,
  collapsed,
  onSelectTopic,
  onCreateTopic,
  onDeleteTopic,
  onToggleCollapse,
}) => {
  const [showDeleteConfirm, setShowDeleteConfirm] = useState<number | null>(null);

  const handleDelete = (e: React.MouseEvent, topicId: number) => {
    e.stopPropagation();
    if (showDeleteConfirm === topicId) {
      onDeleteTopic(topicId);
      setShowDeleteConfirm(null);
    } else {
      setShowDeleteConfirm(topicId);
      // Auto-hide confirmation after 3 seconds
      setTimeout(() => setShowDeleteConfirm(null), 3000);
    }
  };

  const handleCancelDelete = (e: React.MouseEvent) => {
    e.stopPropagation();
    setShowDeleteConfirm(null);
  };

  if (collapsed) {
    return (
      <button
        className={clsx(
          'fixed left-0 top-1/2 -translate-y-1/2 w-16 h-16 bg-white/95 dark:bg-neutral-900/95 backdrop-blur-md shadow-lg border border-neutral-200 dark:border-neutral-700 rounded-r-3xl cursor-pointer hover:border-rose-300 dark:hover:border-rose-600 transition-all duration-300 z-50 flex items-center justify-center text-2xl',
          'hover:pr-4 active:scale-[0.98]'
        )}
        onClick={onToggleCollapse}
        aria-label="展开对话列表"
        title="展开对话列表"
      >
        💬
      </button>
    );
  }

  return (
    <aside className="fixed left-0 top-0 h-full w-72 bg-white/95 dark:bg-neutral-900/95 backdrop-blur-md shadow-lg border-r border-neutral-200 dark:border-neutral-700 z-50 flex flex-col transition-transform duration-300 ease-out">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-neutral-200 dark:border-neutral-700">
        <h2 className="text-lg font-semibold text-neutral-800 dark:text-neutral-100">
          对话
        </h2>
        <button
          className="w-8 h-8 flex items-center justify-center rounded-full text-neutral-400 hover:text-neutral-600 hover:bg-neutral-100 dark:hover:bg-neutral-700 transition-colors"
          onClick={onToggleCollapse}
          aria-label="收起"
          title="收起"
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M15 18l-6-6 6-6"/>
          </svg>
        </button>
      </div>

      {/* New Topic Button */}
      <div className="p-4 border-b border-neutral-200 dark:border-neutral-700">
        <NewTopicButton onClick={onCreateTopic} loading={loading} />
      </div>

      {/* Topics List */}
      <div className="flex-1 overflow-y-auto p-3 scrollbar-elegant">
        {loading && topics.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-neutral-400">
            <div className="w-8 h-8 border-3 border-rose-200 border-t-rose-500 rounded-full animate-spin mb-4"></div>
            <p className="text-sm">加载中...</p>
          </div>
        ) : topics.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-neutral-400 text-center">
            <p className="text-sm mb-1">还没有对话</p>
            <p className="text-xs text-neutral-300">点击上方按钮开始新对话</p>
          </div>
        ) : (
          topics.map((item) => (
            <TopicCard
              key={item.topic.topic_id}
              topic={item}
              isActive={item.topic.topic_id === currentTopicId}
              onClick={() => onSelectTopic(item.topic.topic_id)}
              onDelete={(e) => handleDelete(e, item.topic.topic_id)}
            />
          ))
        )}
      </div>

      {/* Delete Confirmation Modal */}
      {showDeleteConfirm !== null && (
        <div
          className="absolute inset-0 bg-black/20 backdrop-blur-sm animate-fade-in z-10"
          onClick={() => setShowDeleteConfirm(null)}
        >
          <div
            className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-64 bg-white dark:bg-neutral-800 rounded-2xl shadow-xl border border-neutral-200 dark:border-neutral-700 p-5 animate-message-in"
            onClick={(e) => e.stopPropagation()}
          >
            <p className="text-sm text-neutral-700 dark:text-neutral-300 text-center mb-4">
              确定要删除这个对话吗？
            </p>
            <div className="flex gap-2">
              <button
                className="flex-1 px-4 py-2 bg-neutral-100 hover:bg-neutral-200 dark:bg-neutral-700 dark:hover:bg-neutral-600 text-neutral-700 dark:text-neutral-300 rounded-xl text-sm font-medium transition-colors"
                onClick={handleCancelDelete}
              >
                取消
              </button>
              <button
                className="flex-1 px-4 py-2 bg-rose-500 hover:bg-rose-600 text-white rounded-xl text-sm font-medium transition-colors shadow-sm hover:shadow-md"
                onClick={(e) => handleDelete(e, showDeleteConfirm)}
              >
                删除
              </button>
            </div>
          </div>
        </div>
      )}
    </aside>
  );
};
