/** Control Buttons Component */

import React from 'react';
import type { DialoguePhase } from '../../types/chat';

interface ControlButtonsProps {
  phase: DialoguePhase;
  onSend: () => void;
  onNewTurn: () => void;
  canSend: boolean;
  isStreaming: boolean;
}

export const ControlButtons: React.FC<ControlButtonsProps> = ({
  phase,
  onSend,
  // onNewTurn,
  canSend,
  isStreaming,
}) => {
  return (
    <div className="control-buttons">
      {phase === 'user_input' && (
        <button
          className="rpg-btn rpg-btn-primary"
          onClick={onSend}
          disabled={!canSend || isStreaming}
        >
          发送消息
        </button>
      )}

      {/* {phase === 'completed' && (
        <button
          className="rpg-btn rpg-btn-secondary"
          onClick={onNewTurn}
        >
          继续对话
        </button>
      )} */}

      {phase === 'ai_reply' && (
        <div className="rpg-status-text">
          <span>妹妹正在回复</span>
          <span className="loading-dots">...</span>
        </div>
      )}
    </div>
  );
};
