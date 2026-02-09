/** AI Response Area Component - Refined elegant style */

import React, { useState } from 'react';
import { clsx } from 'clsx';

interface AIResponseAreaProps {
  content: string;
  isStreaming: boolean;
  visible: boolean;
  onPlayTTS?: (text: string) => Promise<void>;
}

export const AIResponseArea: React.FC<AIResponseAreaProps> = ({
  content,
  isStreaming,
  visible,
  onPlayTTS,
}) => {
  const [isPlaying, setIsPlaying] = useState(false);

  if (!visible) return null;

  const handlePlayTTS = async () => {
    if (!onPlayTTS || !content || isPlaying) return;

    setIsPlaying(true);
    try {
      await onPlayTTS(content);
    } catch (error) {
      console.error('TTS playback failed:', error);
    } finally {
      setIsPlaying(false);
    }
  };

  return (
    <div className="px-6 pb-6">
      <div className="flex items-center justify-between gap-2 mb-3">
        <label className="text-sm font-medium text-rose-500 dark:text-rose-400">
          妹妹的回复
        </label>
        {onPlayTTS && content && !isStreaming && (
          <button
            className={clsx(
              'w-8 h-8 flex items-center justify-center rounded-lg transition-all',
              'bg-neutral-100 dark:bg-neutral-800 text-neutral-500 hover:text-neutral-700 dark:hover:text-neutral-300',
              isPlaying && 'bg-rose-100 dark:bg-rose-900/30 text-rose-500 animate-pulse-subtle'
            )}
            onClick={handlePlayTTS}
            disabled={isPlaying}
            title="播放语音"
          >
            {isPlaying ? (
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M11 5L6 9H2v6h4l5 4v-14z"/>
                <path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"/>
              </svg>
            ) : (
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M11 5L6 9H2v6h4l5 4V5z"/>
                <path d="M15.54 8.46a5 5 0 0 1 0 7.07" strokeWidth="1.5"/>
                <path d="M19.07 4.93a10 10 0 0 1 0 14.14" strokeWidth="1.5"/>
              </svg>
            )}
          </button>
        )}
      </div>
      <div className="bg-gradient-to-br from-rose-50/50 to-transparent dark:from-rose-950/20 border-2 border-rose-100 dark:border-rose-900/30 rounded-2xl p-5 min-h-[60px]">
        {isStreaming && !content ? (
          <div className="flex items-center gap-1.5 h-10">
            <span className="w-2 h-2 rounded-full bg-rose-400 dark:bg-rose-500 animate-typing"></span>
            <span className="w-2 h-2 rounded-full bg-rose-400 dark:bg-rose-500 animate-typing delay-150"></span>
            <span className="w-2 h-2 rounded-full bg-rose-400 dark:bg-rose-500 animate-typing delay-225"></span>
          </div>
        ) : (
          <div className="text-base leading-relaxed text-neutral-700 dark:text-neutral-300 whitespace-pre-wrap">
            {content || (isStreaming ? '正在思考...' : '')}
          </div>
        )}
      </div>
    </div>
  );
};
