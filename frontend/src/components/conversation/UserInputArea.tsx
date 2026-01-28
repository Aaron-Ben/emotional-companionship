/** User Input Area Component */

import React, { useRef, useEffect, useState, useCallback } from 'react';
import { voiceToText } from '../../services/voiceService';
import type { RecordingState } from '../../types/chat';

interface UserInputAreaProps {
  value: string;
  onChange: (value: string) => void;
  onSend: () => void;
  placeholder?: string;
  disabled?: boolean;
  showSendButton?: boolean;
  canSend?: boolean;
  isStreaming?: boolean;
  onVoiceInputStart?: () => void;
  onVoiceInputEnd?: () => void;
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
  onVoiceInputStart,
  onVoiceInputEnd,
}) => {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [recordingState, setRecordingState] = useState<RecordingState>('idle');
  const [recordingTime, setRecordingTime] = useState(0);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  }, [value]);

  // Recording timer
  useEffect(() => {
    let interval: number | null = null;
    if (recordingState === 'recording') {
      interval = window.setInterval(() => {
        setRecordingTime((prev) => prev + 1);
      }, 1000);
    } else {
      setRecordingTime(0);
    }
    return () => {
      if (interval !== null) {
        clearInterval(interval);
      }
    };
  }, [recordingState]);

  // Handle keyboard shortcuts
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (value.trim() && !disabled) {
        onSend();
      }
    }
  };

  // Handle voice input
  const handleVoiceInput = useCallback(async () => {
    if (recordingState === 'recording') {
      // Stop recording (this shouldn't happen as auto-stop is enabled)
      return;
    }

    setRecordingState('recording');
    onVoiceInputStart?.();

    try {
      const result = await voiceToText(
        { characterId: 'sister_001' },
        30 // max 30 seconds
      );

      if (result.success && result.text) {
        // Append recognized text to current input
        const newText = value + (value ? ' ' : '') + result.text;
        onChange(newText);
      } else if (result.error) {
        console.error('Voice recognition failed:', result.error);
        // Could show a toast notification here
      }
    } catch (error) {
      console.error('Voice input error:', error);
    } finally {
      setRecordingState('idle');
      onVoiceInputEnd?.();
    }
  }, [recordingState, value, onChange, onVoiceInputStart, onVoiceInputEnd]);

  // Format recording time
  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
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
        disabled={disabled || recordingState === 'recording'}
        rows={1}
      />
      <div className="user-input-actions">
        {/* Voice input button */}
        <button
          className={`rpg-btn rpg-btn-voice ${recordingState === 'recording' ? 'recording' : ''}`}
          onClick={handleVoiceInput}
          disabled={disabled || recordingState === 'recording' || isStreaming}
          title={recordingState === 'recording' ? '录音中...' : '语音输入'}
          type="button"
        >
          {recordingState === 'recording' ? (
            <>
              <span className="recording-icon">🎤</span>
              <span className="recording-time">{formatTime(recordingTime)}</span>
            </>
          ) : (
            <span>🎤</span>
          )}
        </button>
        {showSendButton && (
          <button
            className="rpg-btn rpg-btn-primary"
            onClick={onSend}
            disabled={!canSend || isStreaming || recordingState === 'recording'}
          >
            发送
          </button>
        )}
      </div>
    </div>
  );
};
