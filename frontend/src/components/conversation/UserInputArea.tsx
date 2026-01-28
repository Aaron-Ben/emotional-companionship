/** User Input Area Component */

import React, { useRef, useEffect, useState, useCallback } from 'react';
import { AudioRecorder, recognizeFromBlob } from '../../services/voiceService';
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
  const recorderRef = useRef<AudioRecorder | null>(null);
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

  // 按下按钮开始录音
  const handleVoiceStart = useCallback(async () => {
    if (disabled || isStreaming) return;

    try {
      const recorder = new AudioRecorder();
      recorderRef.current = recorder;
      await recorder.start();

      setRecordingState('recording');
      onVoiceInputStart?.();
    } catch (error) {
      console.error('Failed to start recording:', error);
      recorderRef.current = null;
    }
  }, [disabled, isStreaming, onVoiceInputStart]);

  // 松开按钮停止录音并识别
  const handleVoiceEnd = useCallback(async () => {
    if (recordingState !== 'recording' || !recorderRef.current) return;

    setRecordingState('processing');

    try {
      const audioBlob = await recorderRef.current.stop();
      recorderRef.current = null;

      const result = await recognizeFromBlob(audioBlob, { characterId: 'sister_001' });

      if (result.success && result.text) {
        const newText = value + (value ? ' ' : '') + result.text;
        onChange(newText);
      } else if (result.error) {
        console.error('Voice recognition failed:', result.error);
      }
    } catch (error) {
      console.error('Voice input error:', error);
    } finally {
      setRecordingState('idle');
      onVoiceInputEnd?.();
    }
  }, [recordingState, value, onChange, onVoiceInputEnd]);

  // 格式化录音时间
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
        {/* Voice input button - 按住说话 */}
        <button
          className={`rpg-btn rpg-btn-voice ${recordingState === 'recording' ? 'recording' : ''}`}
          onMouseDown={handleVoiceStart}
          onMouseUp={handleVoiceEnd}
          onMouseLeave={handleVoiceEnd}
          onTouchStart={(e) => { e.preventDefault(); handleVoiceStart(); }}
          onTouchEnd={(e) => { e.preventDefault(); handleVoiceEnd(); }}
          disabled={disabled || recordingState !== 'idle' || isStreaming}
          title={
            recordingState === 'recording' ? '松开结束录音' :
            recordingState === 'processing' ? '识别中...' :
            '按住说话'
          }
          type="button"
        >
          {recordingState === 'recording' ? (
            <>
              <span className="recording-icon">🎤</span>
              <span className="recording-time">{formatTime(recordingTime)}</span>
            </>
          ) : recordingState === 'processing' ? (
            <span className="processing">...</span>
          ) : (
            <span>🎤</span>
          )}
        </button>
        {showSendButton && (
          <button
            className="rpg-btn rpg-btn-primary"
            onClick={onSend}
            disabled={!canSend || isStreaming || recordingState !== 'idle'}
          >
            发送
          </button>
        )}
      </div>
    </div>
  );
};
