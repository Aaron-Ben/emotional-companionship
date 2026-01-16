/** Diary delete confirmation modal component */

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
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-[60] p-4"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-2xl shadow-2xl max-w-md w-full p-6"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Icon */}
        <div className="flex justify-center mb-4">
          <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center">
            <span className="text-4xl">🗑️</span>
          </div>
        </div>

        {/* Title */}
        <h3 className="text-xl font-bold text-gray-800 text-center mb-2">
          确定删除日记？
        </h3>

        {/* Message */}
        <p className="text-gray-600 text-center mb-6">
          {diaryDate ? `删除 ${diaryDate} 的日记吗？` : '删除这篇日记吗？'}
          <br />
          <span className="text-sm text-red-500">此操作无法撤销</span>
        </p>

        {/* Buttons */}
        <div className="flex gap-3">
          <button
            onClick={onClose}
            className="flex-1 px-4 py-2.5 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 font-medium"
          >
            取消
          </button>
          <button
            onClick={() => {
              onConfirm();
              onClose();
            }}
            className="flex-1 px-4 py-2.5 bg-red-500 text-white rounded-lg hover:bg-red-600 font-medium"
          >
            确认删除
          </button>
        </div>
      </div>
    </div>
  );
};
