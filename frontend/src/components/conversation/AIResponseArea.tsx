/** AI Response Area Component */

import React, { useState } from 'react';

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
    <div className="ai-response-area">
      <div className="flex items-center justify-between gap-2">
        <label className="input-label">妹妹的回复</label>
        {onPlayTTS && content && !isStreaming && (
          <button
            className={`tts-play-btn ${isPlaying ? 'playing' : ''}`}
            onClick={handlePlayTTS}
            disabled={isPlaying}
            title="播放语音"
          >
            {isPlaying ? '🔊' : '🔇'}
          </button>
        )}
      </div>
      <div className="rpg-response-box">
        {isStreaming && !content ? (
          <div className="response-loading">
            <div className="typing-indicator">
              <div className="typing-dot"></div>
              <div className="typing-dot"></div>
              <div className="typing-dot"></div>
            </div>
          </div>
        ) : (
          <div className="response-content whitespace-pre-wrap">
            {content || (isStreaming ? '正在思考...' : '')}
          </div>
        )}
      </div>
    </div>
  );
};
