/** Diary edit modal component - Refined elegant style */

import React, { useState, useEffect } from 'react';
import { updateDiary, type DiaryEntry, extractDateFromPath } from '../../services/diaryService';

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
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (diary) {
      setContent(diary.content);
    }
  }, [diary]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!diary) return;

    setLoading(true);
    setError(null);

    try {
      const result = await updateDiary(diary.path, content);

      onUpdate?.(result.diary);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update diary');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen || !diary) return null;

  // Extract date from path for display
  const date = extractDateFromPath(diary.path);
  const dateStr = date.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  });

  return (
    <div
      className="fixed inset-0 bg-black/20 backdrop-blur-sm animate-fade-in z-50"
      onClick={onClose}
    >
      <div
        className="mx-4 my-8 max-w-2xl bg-white dark:bg-neutral-800 rounded-3xl shadow-xl border border-neutral-200 dark:border-neutral-700 max-h-[calc(100vh-4rem)] flex flex-col animate-message-in overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="bg-gradient-to-r from-sky-50 to-rose-50/50 dark:from-sky-950/30 dark:to-transparent px-6 py-5 border-b border-sky-100 dark:border-neutral-700">
          <div className="flex justify-between items-center">
            <div>
              <h2 className="text-2xl font-bold text-neutral-800 dark:text-neutral-100">编辑日记</h2>
              <p className="text-sm text-neutral-600 dark:text-neutral-400 mt-1">{dateStr}</p>
            </div>
            <button
              onClick={onClose}
              className="w-8 h-8 flex items-center justify-center rounded-full text-neutral-400 hover:text-neutral-600 hover:bg-neutral-100 dark:hover:bg-neutral-700 transition-colors"
              aria-label="关闭"
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M18 6L6 18M6 6l12 12"/>
              </svg>
            </button>
          </div>
        </div>

        {/* Content */}
        <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto p-6 scrollbar-elegant">
          {error && (
            <div className="mb-4 p-3 bg-rose-100 dark:bg-rose-900/30 border border-rose-300 dark:border-rose-700 text-rose-700 dark:text-rose-400 rounded-xl">
              {error}
            </div>
          )}

          {/* Content */}
          <div className="mb-6">
            <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">
              日记内容（包含末尾的 Tag 行）
            </label>
            <textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              className="w-full h-64 px-4 py-3 bg-neutral-50 dark:bg-neutral-900/50 border-2 border-neutral-200 dark:border-neutral-700 rounded-2xl focus:border-rose-400 dark:focus:border-rose-500 focus:shadow-sm outline-none resize-none transition-all duration-200 text-neutral-800 dark:text-neutral-100"
              placeholder="写下今天发生的事情...&#10;&#10;Tag: 开心, 温暖"
              required
            />
          </div>

          {/* Actions */}
          <div className="flex gap-3 justify-end">
            <button
              type="button"
              onClick={onClose}
              className="px-6 py-2.5 border border-neutral-300 dark:border-neutral-600 text-neutral-700 dark:text-neutral-300 rounded-xl hover:bg-neutral-50 dark:hover:bg-neutral-700 font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              disabled={loading}
            >
              取消
            </button>
            <button
              type="submit"
              className="px-6 py-2.5 bg-gradient-to-r from-rose-400 to-rose-500 hover:from-rose-500 hover:to-rose-600 text-white rounded-xl font-medium transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed shadow-sm hover:shadow-md"
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
