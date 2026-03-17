/** Traditional Chat Panel Component - Refined Elegant Style */

import React, { useRef, useEffect, useState, useCallback } from 'react';
import type { DisplayMessage } from '../../types/chat';
import clsx from 'clsx';
import { AIMessageBubble, AILoadingBubble, UserMessageBubble } from '../chat';

interface TraditionalChatPanelProps {
  messages: DisplayMessage[];
  loading: boolean;
  streamingMessage: string;
  onSendMessage: (content: string) => void;
  placeholder?: string;
  characterId?: string;
  characterName?: string;
}

export const TraditionalChatPanel: React.FC<TraditionalChatPanelProps> = ({
  messages,
  loading,
  streamingMessage,
  onSendMessage,
  placeholder = '聊聊天吧～',
  characterId,
  characterName,
}) => {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingMessage]);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      const newHeight = Math.min(textareaRef.current.scrollHeight, 120);
      textareaRef.current.style.height = `${newHeight}px`;
    }
  }, [input]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleSend = useCallback(() => {
    const trimmedInput = input.trim();
    if (trimmedInput && !loading) {
      onSendMessage(trimmedInput);
      setInput('');
      // Reset textarea height
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
    }
  }, [input, loading, onSendMessage]);

  return (
    <div className="flex flex-col h-full bg-transparent">
      {/* Messages Area */}
      <div
        className="flex-1 overflow-y-auto p-4 md:p-6 scroll-smooth scrollbar-elegant"
        ref={messagesContainerRef}
      >
        <div className="max-w-2xl mx-auto flex flex-col gap-4">
          {messages.length === 0 && !loading && (
            <div className="flex flex-col items-center justify-center min-h-[300px] text-neutral-400 dark:text-neutral-500 gap-4">
              <div className="text-6xl opacity-60">🌸</div>
              <div className="text-base">开始聊天吧～</div>
            </div>
          )}

          {messages.map((message) => (
            <div
              key={message.id}
              className={clsx(
                'flex animate-message-in',
                message.isUser ? 'justify-end' : 'justify-start'
              )}
            >
              {message.isUser ? (
                <UserMessageBubble content={message.content} timestamp={message.timestamp} />
              ) : (
                <AIMessageBubble
                  content={message.content}
                  timestamp={message.timestamp}
                  characterId={characterId}
                  characterName={characterName}
                />
              )}
            </div>
          ))}

          {/* Streaming message */}
          {streamingMessage && (
            <div className="flex justify-start animate-message-in">
              <AIMessageBubble content={streamingMessage} isStreaming={true} />
            </div>
          )}

          {/* Loading indicator */}
          {loading && !streamingMessage && (
            <div className="flex justify-start animate-message-in">
              <AILoadingBubble />
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input Area - 精美的渐变背景和玻璃态效果 */}
      <div className="p-4 md:p-6 bg-gradient-to-t from-rose-50/60 via-rose-50/30 to-transparent dark:from-night-secondary/60 dark:via-night-secondary/30 backdrop-blur-sm border-t border-rose-100/30 dark:border-neutral-800/50">
        <div className="mx-auto max-w-2xl">
          {/* 输入框容器 - 玻璃态效果 */}
          <div className="relative group">
            {/* 发光背景 */}
            <div className="absolute -inset-0.5 bg-gradient-to-r from-rose-200 to-pink-200 dark:from-rose-950 dark:to-pink-950 rounded-full opacity-0 group-hover:opacity-20 transition-opacity duration-300 blur-md"></div>

            <div className="relative flex gap-3 items-end bg-white/90 dark:bg-night-elevated/90 backdrop-blur-md rounded-full px-5 py-3 shadow-soft dark:shadow-dark-soft border-2 border-neutral-200/50 dark:border-neutral-700/50 focus-within:border-rose-300 dark:focus-within:border-rose-700 focus-within:shadow-rose-soft dark:focus-within:shadow-dark-glow transition-all duration-300">
              <textarea
                ref={textareaRef}
                className="flex-1 border-none outline-none text-base bg-transparent text-neutral-700 dark:text-neutral-200 resize-none min-h-[24px] max-h-[120px] leading-relaxed placeholder:text-neutral-400 dark:placeholder:text-neutral-500 disabled:opacity-60 disabled:cursor-not-allowed"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={placeholder}
                disabled={loading}
                rows={1}
              />
              <div className="flex items-center gap-2">
                {/* Send button - 精美的渐变和发光效果 */}
                <button
                  className={clsx(
                    'w-10 h-10 rounded-full flex items-center justify-center gap-1 shrink-0 text-sm font-semibold transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed active:scale-95',
                    input.trim() && !loading
                      ? 'bg-gradient-to-r from-rose-400 via-rose-500 to-pink-500 text-white shadow-rose-soft hover:shadow-rose-soft-lg hover:-translate-y-0.5'
                      : 'bg-gradient-to-r from-neutral-300 to-neutral-400 dark:from-neutral-600 dark:to-neutral-700 text-neutral-500 dark:text-neutral-400'
                  )}
                  onClick={handleSend}
                  disabled={!input.trim() || loading}
                  title="发送"
                  type="button"
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="shrink-0">
                    <path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z"/>
                  </svg>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
