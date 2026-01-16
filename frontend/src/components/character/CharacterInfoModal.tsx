/** Character info modal component */

import React from 'react';
import { Modal } from '../ui/Modal';
import { CharacterAvatar } from './CharacterAvatar';
import type { CharacterTemplate } from '../../types/character';

interface CharacterInfoModalProps {
  isOpen: boolean;
  onClose: () => void;
  character: CharacterTemplate | null;
}

export const CharacterInfoModal: React.FC<CharacterInfoModalProps> = ({
  isOpen,
  onClose,
  character,
}) => {
  if (!character) return null;

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={character.name}>
      <div className="space-y-6">
        {/* Avatar */}
        <div className="flex justify-center">
          <CharacterAvatar size="large" />
        </div>

        {/* Basic Info */}
        <div className="text-center">
          <h3 className="text-xl font-semibold text-pink-600 mb-2">
            {character.name}
          </h3>
          <p className="text-gray-600 text-sm">{character.identity.description}</p>
        </div>

        {/* Traits */}
        <div>
          <h4 className="text-sm font-semibold text-gray-700 mb-2">性格特征</h4>
          <div className="flex flex-wrap gap-2">
            {character.identity.personality_traits.map((trait) => (
              <span key={trait} className="tag">
                {trait === 'affectionate' && '亲昵'}
                {trait === 'playful' && '顽皮'}
                {trait === 'caring' && '关心人'}
                {trait === 'opinionated' && '有主见'}
                {trait === 'sometimes_jealous' && '会吃醋'}
                {trait === 'proactive' && '主动'}
              </span>
            ))}
          </div>
        </div>

        {/* Details */}
        <div className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-gray-600">角色</span>
            <span className="font-medium">{character.identity.role}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-600">年龄</span>
            <span className="font-medium">{character.identity.age}岁</span>
          </div>
          <div className="flex justify-between">
            <span class="text-gray-600">称呼你</span>
            <span className="font-medium">{character.base_nickname}</span>
          </div>
        </div>

        {/* Behavior */}
        <div>
          <h4 className="text-sm font-semibold text-gray-700 mb-2">互动特点</h4>
          <ul className="text-sm text-gray-600 space-y-1">
            <li>• 情绪敏感度: {Math.round(character.behavior.emotional_sensitivity * 100)}%</li>
            <li>• 主动性: {Math.round(character.behavior.proactivity_level * 100)}%</li>
            <li>• 有自己的主见，偶尔会小争执</li>
            <li>• 会根据你的情绪调整回应方式</li>
          </ul>
        </div>
      </div>
    </Modal>
  );
};
