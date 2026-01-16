/** Typing indicator component for showing when character is "thinking" */

import React from 'react';

export const TypingIndicator: React.FC = () => {
  return (
    <div className="message-bubble character">
      <div className="typing-indicator">
        <span className="typing-dot" />
        <span className="typing-dot" />
        <span className="typing-dot" />
      </div>
    </div>
  );
};
