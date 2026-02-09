/** User Input Area Component - Refined elegant style */

import React, { useRef, useEffect, useState, useCallback } from 'react';
import { AudioRecorder, recognizeFromBlob } from '../../services/voiceService';
import type { RecordingState } from '../../types/chat';
import { clsx } from 'clsx';

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

  // Voice input start
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

  // Voice input end
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

  // Format recording time
  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="p-6">
      <textarea
        ref={textareaRef}
        className="w-full px-4 py-3 bg-neutral-50 dark:bg-neutral-900/50 border-2 border-neutral-200 dark:border-neutral-700 rounded-2xl text-base text-neutral-800 dark:text-neutral-100 placeholder:text-neutral-400 resize-none outline-none focus:border-rose-400 dark:focus:border-rose-500 focus:shadow-sm transition-all duration-200 min-h-[48px] max-h-[120px]"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        disabled={disabled || recordingState === 'recording'}
        rows={1}
      />
      <div className="flex items-center gap-3 mt-4 justify-end">
        {/* Voice input button */}
        <button
          className={clsx(
            'px-5 py-2.5 rounded-xl font-medium text-sm transition-all duration-200 flex items-center gap-2 active:scale-[0.98]',
            recordingState === 'recording'
              ? 'bg-rose-400 hover:bg-rose-500 text-white'
              : 'bg-emerald-400 hover:bg-emerald-500 dark:bg-emerald-500 dark:hover:bg-emerald-600 text-white',
            'disabled:opacity-50 disabled:cursor-not-allowed'
          )}
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
              <span>🎤</span>
              <span className="text-sm font-semibold tabular-nums">{formatTime(recordingTime)}</span>
            </>
          ) : recordingState === 'processing' ? (
            <>
              <span className="animate-spin">⌛</span>
              <span className="text-sm">识别中...</span>
            </>
          ) : (
            <>
              <span>🎤</span>
              <span className="text-sm">按住说话</span>
            </>
          )}
        </button>
        {showSendButton && (
          <button
            className="px-6 py-2.5 bg-gradient-to-r from-rose-400 to-rose-500 hover:from-rose-500 hover:to-rose-600 text-white rounded-xl font-medium text-sm shadow-sm hover:shadow-md transition-all duration-200 active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed"
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
