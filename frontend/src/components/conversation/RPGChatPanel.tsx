/** RPG Style Chat Panel Component */

import React from 'react';
import { UserInputArea } from './UserInputArea';
import { AIResponseArea } from './AIResponseArea';
import type { DialoguePhase } from '../../types/chat';

interface RPGChatPanelProps {
  phase: DialoguePhase;
  userInput: string;
  aiResponse: string;
  isStreaming: boolean;
  onUserInputChange: (value: string) => void;
  onSend: () => void;
  onNewTurn: () => void;
  placeholder?: string;
  onVoiceInputStart?: () => void;
  onVoiceInputEnd?: () => void;
  onPlayTTS?: (text: string) => Promise<void>;
}

export const RPGChatPanel: React.FC<RPGChatPanelProps> = ({
  phase,
  userInput,
  aiResponse,
  isStreaming,
  onUserInputChange,
  onSend,
  onNewTurn,
  placeholder = '输入你想说的话...',
  onVoiceInputStart,
  onVoiceInputEnd,
  onPlayTTS,
}) => {
  const showAIResponse = phase === 'ai_reply' || phase === 'completed';
  const showSendButton = phase === 'user_input';

  return (
    <div className="rpg-chat-panel">
      <div className="rpg-panel-border">
        {/* User input area with send button */}
        <UserInputArea
          value={userInput}
          onChange={onUserInputChange}
          onSend={onSend}
          placeholder={placeholder}
          disabled={phase === 'ai_reply' || isStreaming}
          showSendButton={showSendButton}
          canSend={userInput.trim().length > 0}
          isStreaming={isStreaming}
          onVoiceInputStart={onVoiceInputStart}
          onVoiceInputEnd={onVoiceInputEnd}
        />

        {/* AI response area */}
        <AIResponseArea
          content={aiResponse}
          isStreaming={isStreaming}
          visible={showAIResponse}
          onPlayTTS={onPlayTTS}
        />

        {/* Loading status */}
        {phase === 'ai_reply' && (
          <div className="control-buttons">
            <div className="rpg-status-text">
              <span>妹妹正在回复</span>
              <span className="loading-dots">...</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
