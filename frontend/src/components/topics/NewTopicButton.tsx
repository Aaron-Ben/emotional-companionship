/** New topic button component */

import React from 'react';

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
      className="new-topic-btn"
      onClick={onClick}
      disabled={disabled || loading}
      aria-label="新对话"
      title="开始新对话"
    >
      {loading ? (
        <span className="new-topic-loading">...</span>
      ) : (
        <>
          <span className="new-topic-icon">+</span>
          <span className="new-topic-text">新对话</span>
        </>
      )}
    </button>
  );
};
