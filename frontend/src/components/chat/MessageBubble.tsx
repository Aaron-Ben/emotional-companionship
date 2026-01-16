/** Message bubble component with anime style */

import React from 'react';
import type { DisplayMessage } from '../../types/chat';

interface MessageBubbleProps {
  message: DisplayMessage;
}

export const MessageBubble: React.FC<MessageBubbleProps> = ({ message }) => {
  const formatTime = (date: Date) => {
    return new Intl.DateTimeFormat('zh-CN', {
      hour: '2-digit',
      minute: '2-digit',
    }).format(date);
  };

  return (
    <div className={`message-bubble ${message.isUser ? 'user' : 'character'}`}>
      <div className="message-content whitespace-pre-wrap">{message.content}</div>
      <div className="message-time">{formatTime(message.timestamp)}</div>
    </div>
  );
};
