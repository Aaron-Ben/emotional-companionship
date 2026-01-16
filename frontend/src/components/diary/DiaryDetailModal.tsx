/** Diary detail modal component */

import React from 'react';
import { DiaryEntry } from '../../services/diaryService';

interface DiaryDetailModalProps {
  diary: DiaryEntry | null;
  isOpen: boolean;
  onClose: () => void;
}

export const DiaryDetailModal: React.FC<DiaryDetailModalProps> = ({
  diary,
  isOpen,
  onClose
}) => {
  if (!isOpen || !diary) return null;

  const dateObj = new Date(diary.date);
  const weekdays = ['星期日', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六'];

  return (
    <div
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full max-h-[80vh] overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="bg-gradient-to-r from-pink-100 via-purple-100 to-pink-100 px-6 py-5 border-b border-pink-200">
          <div className="flex justify-between items-start">
            <div className="flex-1">
              <div className="flex items-center gap-3 mb-2">
                <span className="text-3xl">📔</span>
                <h2 className="text-2xl font-bold text-gray-800">妹妹的日记</h2>
              </div>
              <p className="text-sm text-gray-600">
                {dateObj.toLocaleDateString('zh-CN', {
                  year: 'numeric',
                  month: 'long',
                  day: 'numeric',
                  weekday: 'long'
                })}
              </p>
            </div>
            <button
              onClick={onClose}
              className="text-gray-500 hover:text-gray-700 text-3xl leading-none ml-4"
            >
              ×
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {/* Diary content */}
          <div className="mb-6">
            <div className="prose prose-sm max-w-none">
              <p className="text-gray-700 leading-loose whitespace-pre-wrap text-base">
                {diary.content}
              </p>
            </div>
          </div>

          {/* Tags */}
          {diary.tags.length > 0 && (
            <div className="mb-6 pt-4 border-t border-pink-100">
              <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
                <span>🏷️</span>
                <span>标签</span>
              </h3>
              <div className="flex gap-2 flex-wrap">
                {diary.tags.map((tag) => (
                  <span
                    key={tag}
                    className="px-3 py-1.5 bg-gradient-to-r from-pink-50 to-purple-50 text-pink-600 rounded-full text-sm font-medium border border-pink-200"
                  >
                    #{tag}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Emotions */}
          {diary.emotions.length > 0 && (
            <div className="mb-6 pt-4 border-t border-pink-100">
              <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
                <span>💭</span>
                <span>心情</span>
              </h3>
              <div className="flex gap-2 flex-wrap">
                {diary.emotions.map((emotion) => (
                  <span
                    key={emotion}
                    className="px-3 py-1.5 bg-pink-100 text-pink-700 rounded-lg text-sm font-medium"
                  >
                    {emotion}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Metadata */}
          <div className="pt-4 border-t border-gray-200 text-xs text-gray-500 space-y-1">
            <p>触发类型: {diary.trigger_type}</p>
            <p>创建时间: {new Date(diary.created_at).toLocaleString('zh-CN')}</p>
          </div>
        </div>
      </div>
    </div>
  );
};
