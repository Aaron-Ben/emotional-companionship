/** RPG Style Chat Panel Component - Refined Elegant Style */

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
  placeholder = '输入你想说的话...',
  onVoiceInputStart,
  onVoiceInputEnd,
  onPlayTTS,
}) => {
  const showAIResponse = phase === 'ai_reply' || phase === 'completed';
  const showSendButton = phase === 'user_input';

  return (
    <div className="fixed bottom-0 left-0 right-0 z-40">
      <div className="mx-auto max-w-3xl">
        <div className="bg-white/95 dark:bg-neutral-900/95 backdrop-blur-sm rounded-t-3xl border border-neutral-200 dark:border-neutral-700 border-b-0 shadow-xl">
          {/* Fixed height content area */}
          <div className="p-6 h-[320px] flex flex-col">
            {/* AI response area - takes available space, always renders to maintain size */}
            <div className="flex-1 min-h-0 relative">
              <AIResponseArea
                content={aiResponse}
                isStreaming={isStreaming}
                visible={showAIResponse}
                onPlayTTS={onPlayTTS}
              />

              {/* Loading status - absolute positioned overlay */}
              {phase === 'ai_reply' && !aiResponse && (
                <div className="absolute inset-0 flex items-center justify-center bg-white/50 dark:bg-neutral-800/50 rounded-2xl">
                  <div className="flex items-center gap-2 text-rose-500 dark:text-rose-400 text-sm font-medium">
                    <span>妹妹正在回复</span>
                    <div className="flex gap-1">
                      <span className="w-1.5 h-1.5 rounded-full bg-rose-500 animate-typing"></span>
                      <span className="w-1.5 h-1.5 rounded-full bg-rose-500 animate-typing delay-150"></span>
                      <span className="w-1.5 h-1.5 rounded-full bg-rose-500 animate-typing delay-225"></span>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* User input area - fixed at bottom */}
            <div className="mt-4">
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
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
