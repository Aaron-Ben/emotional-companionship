/** User Input Area Component */

import React, { useRef, useEffect } from 'react';

interface UserInputAreaProps {
  value: string;
  onChange: (value: string) => void;
  onSend: () => void;
  placeholder?: string;
  disabled?: boolean;
  showSendButton?: boolean;
  canSend?: boolean;
  isStreaming?: boolean;
}

export const UserInputArea: React.FC<UserInputAreaProps> = ({
  value,
  onChange,
  onSend,
  placeholder = '输入你想说的话...',
  disabled,
  showSendButton = false,
  canSend = false,
  isStreaming = false,
}) => {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  }, [value]);

  // Handle keyboard shortcuts
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (value.trim() && !disabled) {
        onSend();
      }
    }
  };

  return (
    <div className="user-input-area">
      <textarea
        ref={textareaRef}
        className="rpg-textarea"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        disabled={disabled}
        rows={1}
      />
      {showSendButton && (
        <button
          className="rpg-btn rpg-btn-primary"
          onClick={onSend}
          disabled={!canSend || isStreaming}
        >
          发送
        </button>
      )}
    </div>
  );
};
