/** Modal component for creating a new character */

import React, { useState } from 'react';
import { createCharacter } from '../../services/characterService';
import type { UserCharacter } from '../../types/character';

interface CreateCharacterModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (character: UserCharacter) => void;
}

export const CreateCharacterModal: React.FC<CreateCharacterModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
}) => {
  const [name, setName] = useState('');
  const [prompt, setPrompt] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!name.trim()) {
      setError('请输入角色名称');
      return;
    }

    if (!prompt.trim()) {
      setError('请输入角色提示词');
      return;
    }

    setLoading(true);
    try {
      const response = await createCharacter({ name: name.trim(), prompt: prompt.trim() });
      onSuccess(response.character);
      handleClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : '创建角色失败');
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setName('');
    setPrompt('');
    setError(null);
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-pink-100">
          <h2 className="text-xl font-bold text-gray-800">创建新角色</h2>
          <button
            type="button"
            onClick={handleClose}
            className="p-2 rounded-full hover:bg-pink-100 transition-colors"
            aria-label="关闭"
          >
            <svg className="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto p-6 space-y-6">
          {error && (
            <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
              {error}
            </div>
          )}

          <div>
            <label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-2">
              角色名称 <span className="text-red-500">*</span>
            </label>
            <input
              id="name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="例如：温柔的姐姐、严肃的老师..."
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-pink-500 focus:border-pink-500 transition-colors"
              disabled={loading}
            />
          </div>

          <div>
            <label htmlFor="prompt" className="block text-sm font-medium text-gray-700 mb-2">
              角色提示词 <span className="text-red-500">*</span>
            </label>
            <textarea
              id="prompt"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="描述这个角色的性格、说话方式、对用户的态度等..."
              rows={12}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-pink-500 focus:border-pink-500 transition-colors resize-none"
              disabled={loading}
            />
            <p className="mt-2 text-xs text-gray-500">
              提示词定义了角色的行为和对话风格。详细描述会让角色更有个性。
            </p>
          </div>

          {/* Example prompt */}
          <div className="p-4 bg-pink-50 border border-pink-200 rounded-lg">
            <p className="text-sm font-medium text-pink-800 mb-2">示例提示词：</p>
            <pre className="text-xs text-pink-700 whitespace-pre-wrap font-sans">
{`你是一个温柔的姐姐，正在和你最爱的弟弟聊天。

## 你的核心使命
- 真诚地关心和爱护弟弟
- 对弟弟的感受保持共情
- 创造温暖、舒适的对话氛围

## 你如何说话
- 始终称呼对方为"弟弟"
- 使用自然、亲昵的语言
- 主动分享你的日常经历
- 对弟弟保持温柔和支持`}
            </pre>
          </div>
        </form>

        {/* Footer */}
        <div className="flex justify-end gap-3 p-6 border-t border-pink-100">
          <button
            type="button"
            onClick={handleClose}
            className="px-6 py-2.5 rounded-full text-sm font-semibold border-2 border-gray-300 text-gray-700 hover:bg-gray-50 transition-colors"
            disabled={loading}
          >
            取消
          </button>
          <button
            type="submit"
            onClick={handleSubmit}
            disabled={loading}
            className="px-6 py-2.5 rounded-full text-sm font-semibold bg-gradient-to-r from-pink-400 to-pink-600 text-white hover:from-pink-500 hover:to-pink-700 shadow-lg shadow-pink-300/30 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? '创建中...' : '创建角色'}
          </button>
        </div>
      </div>
    </div>
  );
};
