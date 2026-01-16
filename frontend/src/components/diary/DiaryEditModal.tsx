/** Diary edit modal component */

import React, { useState, useEffect } from 'react';
import { updateDiary, type DiaryEntry } from '../../services/diaryService';

interface DiaryEditModalProps {
  isOpen: boolean;
  onClose: () => void;
  diary: DiaryEntry | null;
  onUpdate?: (diary: DiaryEntry) => void;
}

export const DiaryEditModal: React.FC<DiaryEditModalProps> = ({
  isOpen,
  onClose,
  diary,
  onUpdate
}) => {
  const [content, setContent] = useState('');
  const [emotions, setEmotions] = useState<string[]>([]);
  const [tags, setTags] = useState<string[]>([]);
  const [emotionInput, setEmotionInput] = useState('');
  const [tagInput, setTagInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (diary) {
      setContent(diary.content);
      setEmotions(diary.emotions || []);
      setTags(diary.tags || []);
    }
  }, [diary]);

  const handleAddEmotion = () => {
    if (emotionInput.trim() && !emotions.includes(emotionInput.trim())) {
      setEmotions([...emotions, emotionInput.trim()]);
      setEmotionInput('');
    }
  };

  const handleRemoveEmotion = (emotion: string) => {
    setEmotions(emotions.filter(e => e !== emotion));
  };

  const handleAddTag = () => {
    if (tagInput.trim() && !tags.includes(tagInput.trim())) {
      setTags([...tags, tagInput.trim()]);
      setTagInput('');
    }
  };

  const handleRemoveTag = (tag: string) => {
    setTags(tags.filter(t => t !== tag));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!diary) return;

    setLoading(true);
    setError(null);

    try {
      const result = await updateDiary(diary.id, {
        content,
        emotions,
        tags
      });

      onUpdate?.(result.diary);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update diary');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen || !diary) return null;

  return (
    <div
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="bg-gradient-to-r from-blue-100 to-purple-100 px-6 py-4 border-b border-blue-200">
          <div className="flex justify-between items-center">
            <div>
              <h2 className="text-2xl font-bold text-gray-800">编辑日记</h2>
              <p className="text-sm text-gray-600 mt-1">{diary.date}</p>
            </div>
            <button
              onClick={onClose}
              className="text-gray-500 hover:text-gray-700 text-2xl leading-none"
            >
              ×
            </button>
          </div>
        </div>

        {/* Content */}
        <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto p-6">
          {error && (
            <div className="mb-4 p-3 bg-red-100 border border-red-300 text-red-700 rounded-lg">
              {error}
            </div>
          )}

          {/* Content */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              日记内容
            </label>
            <textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              className="w-full h-64 px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-pink-500 focus:border-transparent resize-none"
              placeholder="写下今天发生的事情..."
              required
            />
          </div>

          {/* Emotions */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              情绪标签
            </label>
            <div className="flex gap-2 mb-2">
              <input
                type="text"
                value={emotionInput}
                onChange={(e) => setEmotionInput(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), handleAddEmotion())}
                className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-pink-500 focus:border-transparent"
                placeholder="添加情绪..."
              />
              <button
                type="button"
                onClick={handleAddEmotion}
                className="px-4 py-2 bg-pink-500 text-white rounded-lg hover:bg-pink-600"
              >
                添加
              </button>
            </div>
            <div className="flex flex-wrap gap-2">
              {emotions.map((emotion) => (
                <span
                  key={emotion}
                  className="inline-flex items-center gap-1 px-3 py-1 bg-pink-100 text-pink-700 rounded-full text-sm"
                >
                  {emotion}
                  <button
                    type="button"
                    onClick={() => handleRemoveEmotion(emotion)}
                    className="hover:text-pink-900"
                  >
                    ×
                  </button>
                </span>
              ))}
            </div>
          </div>

          {/* Tags */}
          <div className="mb-6">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              内容标签
            </label>
            <div className="flex gap-2 mb-2">
              <input
                type="text"
                value={tagInput}
                onChange={(e) => setTagInput(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), handleAddTag())}
                className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-pink-500 focus:border-transparent"
                placeholder="添加标签..."
              />
              <button
                type="button"
                onClick={handleAddTag}
                className="px-4 py-2 bg-purple-500 text-white rounded-lg hover:bg-purple-600"
              >
                添加
              </button>
            </div>
            <div className="flex flex-wrap gap-2">
              {tags.map((tag) => (
                <span
                  key={tag}
                  className="inline-flex items-center gap-1 px-3 py-1 bg-purple-100 text-purple-700 rounded-full text-sm"
                >
                  #{tag}
                  <button
                    type="button"
                    onClick={() => handleRemoveTag(tag)}
                    className="hover:text-purple-900"
                  >
                    ×
                  </button>
                </span>
              ))}
            </div>
          </div>

          {/* Actions */}
          <div className="flex gap-3 justify-end">
            <button
              type="button"
              onClick={onClose}
              className="px-6 py-2.5 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
              disabled={loading}
            >
              取消
            </button>
            <button
              type="submit"
              className="px-6 py-2.5 bg-gradient-to-r from-pink-500 to-purple-500 text-white rounded-lg hover:from-pink-600 hover:to-purple-600 disabled:opacity-50 disabled:cursor-not-allowed"
              disabled={loading}
            >
              {loading ? '保存中...' : '保存修改'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
