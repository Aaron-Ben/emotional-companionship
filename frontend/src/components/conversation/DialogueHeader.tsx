/** Dialogue Header Component - Displays current conversation turn */

import React from 'react';
import type { CurrentTurn } from '../../types/chat';

interface DialogueHeaderProps {
  currentTurn: CurrentTurn;
  characterName?: string;
}

export const DialogueHeader: React.FC<DialogueHeaderProps> = ({
  currentTurn,
  characterName = '妹妹'
}) => {
  return (
    <div className="dialogue-header">
      {/* User message display */}
      {currentTurn.userMessage && (
        <div className="dialogue-message user">
          <div className="message-label">你</div>
          <div className="message-content">{currentTurn.userMessage}</div>
        </div>
      )}

      {/* AI message display */}
      {currentTurn.aiMessage && (
        <div className="dialogue-message character">
          <div className="message-label">{characterName}</div>
          <div className="message-content whitespace-pre-wrap">{currentTurn.aiMessage}</div>
        </div>
      )}

      {/* Empty state */}
      {!currentTurn.userMessage && !currentTurn.aiMessage && (
        <div className="dialogue-empty">
          <p>开始和{characterName}聊天吧～</p>
        </div>
      )}
    </div>
  );
};
