/** Character avatar component */

import React from 'react';

interface CharacterAvatarProps {
  size?: 'small' | 'medium' | 'large';
  emoji?: string;
}

export const CharacterAvatar: React.FC<CharacterAvatarProps> = ({
  size = 'medium',
  emoji = '👧',
}) => {
  const sizeClasses = {
    small: 'w-12 h-12 text-2xl',
    medium: 'w-20 h-20 text-4xl',
    large: 'w-32 h-32 text-6xl',
  };

  return (
    <div className={`character-avatar ${sizeClasses[size]} flex items-center justify-center`}>
      {emoji}
    </div>
  );
};
