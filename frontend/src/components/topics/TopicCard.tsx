/** Individual topic card component */

import React from 'react';
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
      className={`topic-card ${isActive ? 'topic-card-active' : ''}`}
      onClick={onClick}
    >
      <div className="topic-card-content">
        <div className="topic-preview">{previewText}</div>
        <div className="topic-meta">
          <span className="topic-time">{topic.timeAgo}</span>
          {topic.topic.message_count > 0 && (
            <span className="topic-badge">{topic.topic.message_count}</span>
          )}
        </div>
      </div>
      <button
        className="topic-delete-btn"
        onClick={onDelete}
        aria-label="删除对话"
        title="删除对话"
      >
        ×
      </button>
    </div>
  );
};
