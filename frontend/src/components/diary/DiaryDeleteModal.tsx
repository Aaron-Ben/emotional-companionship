/** Diary delete confirmation modal component - Refined elegant style */

import React from 'react';

interface DiaryDeleteModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  diaryDate?: string;
}

export const DiaryDeleteModal: React.FC<DiaryDeleteModalProps> = ({
  isOpen,
  onClose,
  onConfirm,
  diaryDate
}) => {
  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 bg-black/20 backdrop-blur-sm animate-fade-in z-[60]"
      onClick={onClose}
    >
      <div
        className="mx-4 max-w-md bg-white dark:bg-neutral-800 rounded-3xl shadow-xl border border-neutral-200 dark:border-neutral-700 p-6 animate-message-in"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Icon */}
        <div className="flex justify-center mb-4">
          <div className="w-16 h-16 bg-rose-100 dark:bg-rose-900/30 rounded-full flex items-center justify-center">
            <span className="text-4xl">🗑️</span>
          </div>
        </div>

        {/* Title */}
        <h3 className="text-xl font-bold text-neutral-800 dark:text-neutral-100 text-center mb-2">
          确定删除日记？
        </h3>

        {/* Message */}
        <p className="text-neutral-600 dark:text-neutral-400 text-center mb-6">
          {diaryDate ? `删除 ${diaryDate} 的日记吗？` : '删除这篇日记吗？'}
          <br />
          <span className="text-sm text-rose-500">此操作无法撤销</span>
        </p>

        {/* Buttons */}
        <div className="flex gap-3">
          <button
            onClick={onClose}
            className="flex-1 px-4 py-2.5 border border-neutral-300 dark:border-neutral-600 text-neutral-700 dark:text-neutral-300 rounded-xl hover:bg-neutral-50 dark:hover:bg-neutral-700 font-medium transition-colors"
          >
            取消
          </button>
          <button
            onClick={() => {
              onConfirm();
              onClose();
            }}
            className="flex-1 px-4 py-2.5 bg-rose-500 hover:bg-rose-600 text-white rounded-xl font-medium transition-colors shadow-sm hover:shadow-md"
          >
            确认删除
          </button>
        </div>
      </div>
    </div>
  );
};
