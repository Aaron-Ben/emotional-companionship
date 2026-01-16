/** AI Response Area Component */

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
    <div className="ai-response-area">
      <label className="input-label">妹妹的回复</label>
      <div className="rpg-response-box">
        {isStreaming && !content ? (
          <div className="response-loading">
            <div className="typing-indicator">
              <div className="typing-dot"></div>
              <div className="typing-dot"></div>
              <div className="typing-dot"></div>
            </div>
          </div>
        ) : (
          <div className="response-content whitespace-pre-wrap">
            {content || (isStreaming ? '正在思考...' : '')}
          </div>
        )}
      </div>
    </div>
  );
};
