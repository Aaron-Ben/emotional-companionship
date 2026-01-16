/** Welcome page with character introduction */

import React, { useEffect, useState } from 'react';
import { Button } from '../components/ui/Button';
import { CharacterAvatar } from '../components/character/CharacterAvatar';
import { useCharacter } from '../hooks/useCharacter';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';

interface WelcomePageProps {
  onStartChat: () => void;
}

export const WelcomePage: React.FC<WelcomePageProps> = ({ onStartChat }) => {
  const { character, loading, getStarter } = useCharacter('sister_001');
  const [starter, setStarter] = useState<string | null>(null);

  useEffect(() => {
    if (character) {
      getStarter().then(setStarter);
    }
  }, [character, getStarter]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <LoadingSpinner size="large" />
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4 relative overflow-hidden">
      {/* Decorative elements */}
      <div className="decoration-star" style={{ top: '10%', left: '15%' }}>✨</div>
      <div className="decoration-star" style={{ top: '20%', right: '20%' }}>✨</div>
      <div className="decoration-heart" style={{ bottom: '30%', left: '10%' }}>💕</div>
      <div className="decoration-heart" style={{ bottom: '20%', right: '15%' }}>💕</div>

      <div className="anime-card max-w-md w-full text-center relative z-10">
        {/* Character Avatar */}
        <div className="flex justify-center mb-6">
          <CharacterAvatar size="large" />
        </div>

        {/* Title */}
        <h1 className="text-3xl font-bold text-pink-600 mb-2">
          {character?.name || '妹妹'}
        </h1>
        <p className="text-gray-600 mb-6">{character?.identity.description}</p>

        {/* Personality Traits */}
        <div className="mb-8">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">性格特点</h3>
          <div className="flex flex-wrap justify-center gap-2">
            {character?.identity.personality_traits.map((trait) => (
              <span key={trait} className="tag">
                {trait === 'affectionate' && '🥰 亲昵撒娇'}
                {trait === 'playful' && '😊 顽皮可爱'}
                {trait === 'caring' && '💝 关心体贴'}
                {trait === 'opinionated' && '💪 有主见'}
                {trait === 'sometimes_jealous' && '😤 会吃醋'}
                {trait === 'proactive' && '🌟 主动互动'}
              </span>
            ))}
          </div>
        </div>

        {/* Starter Message */}
        {starter && (
          <div className="bg-pink-50 rounded-lg p-4 mb-8 border-2 border-pink-100">
            <p className="text-gray-700 text-sm italic">"{starter}"</p>
          </div>
        )}

        {/* Call to Action */}
        <div className="space-y-4">
          <Button onClick={onStartChat} className="w-full text-lg py-4">
            开始聊天 💬
          </Button>
          <p className="text-xs text-gray-500">
            你的贴心妹妹，随时陪伴在你身边～
          </p>
        </div>
      </div>
    </div>
  );
};
