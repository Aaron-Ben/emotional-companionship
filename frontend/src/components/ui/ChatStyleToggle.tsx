/** Chat Style Toggle Button Component */

import React from 'react';
import type { ChatStyle } from '../../hooks/useChatStyle';
import { ControlButton } from './ControlButton';

interface ChatStyleToggleProps {
  currentStyle: ChatStyle;
  onToggle: () => void;
}

export const ChatStyleToggle: React.FC<ChatStyleToggleProps> = ({
  currentStyle,
  onToggle,
}) => {
  const isRPG = currentStyle === 'rpg';
  const nextLabel = isRPG ? '切换到传统对话' : '切换到RPG对话';
  const label = isRPG ? 'RPG模式' : '传统模式';

  return (
    <div className="fixed top-4 right-4 z-[1000]">
      <ControlButton
        icon={null}
        label={label}
        onClick={onToggle}
        title={nextLabel}
      />
    </div>
  );
};
