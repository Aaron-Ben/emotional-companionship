/** Diary detail modal component */

import React from 'react';
import { DiaryEntry, extractDateFromPath } from '../../services/diaryService';

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

  // Extract date from path
  const date = extractDateFromPath(diary.path);

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
                {date.toLocaleDateString('zh-CN', {
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

          {/* Metadata */}
          <div className="pt-4 border-t border-gray-200 text-xs text-gray-500 space-y-1">
            <p>日记本: {diary.diary_name}</p>
            <p>文件路径: {diary.path}</p>
            <p>修改时间: {new Date(diary.mtime * 1000).toLocaleString('zh-CN')}</p>
          </div>
        </div>
      </div>
    </div>
  );
};
