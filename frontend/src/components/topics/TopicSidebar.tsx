/** Topic sidebar component */

import React, { useState } from 'react';
import type { TopicListItem } from '../../types/chat';
import { TopicCard } from './TopicCard';
import { NewTopicButton } from './NewTopicButton';

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
        className="topic-sidebar-toggle topic-sidebar-toggle-collapsed"
        onClick={onToggleCollapse}
        aria-label="展开对话列表"
        title="展开对话列表"
      >
        <span>💬</span>
      </button>
    );
  }

  return (
    <aside className="topic-sidebar">
      {/* Header */}
      <div className="topic-sidebar-header">
        <h2 className="topic-sidebar-title">对话</h2>
        <button
          className="topic-sidebar-collapse"
          onClick={onToggleCollapse}
          aria-label="收起"
          title="收起"
        >
          ‹
        </button>
      </div>

      {/* New Topic Button */}
      <div className="topic-sidebar-new">
        <NewTopicButton onClick={onCreateTopic} loading={loading} />
      </div>

      {/* Topics List */}
      <div className="topic-sidebar-list">
        {loading && topics.length === 0 ? (
          <div className="topic-sidebar-empty">
            <div className="topic-loading-spinner" />
            <p>加载中...</p>
          </div>
        ) : topics.length === 0 ? (
          <div className="topic-sidebar-empty">
            <p>还没有对话</p>
            <p className="topic-sidebar-hint">点击上方按钮开始新对话</p>
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
        <div className="topic-delete-confirm-overlay" onClick={() => setShowDeleteConfirm(null)}>
          <div className="topic-delete-confirm" onClick={(e) => e.stopPropagation()}>
            <p>确定要删除这个对话吗？</p>
            <div className="topic-delete-confirm-actions">
              <button
                className="topic-delete-confirm-btn topic-delete-confirm-cancel"
                onClick={handleCancelDelete}
              >
                取消
              </button>
              <button
                className="topic-delete-confirm-btn topic-delete-confirm-ok"
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
