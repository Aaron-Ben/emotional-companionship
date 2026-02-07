/** Diary card component for displaying a single diary entry */

import React from 'react';
import { DiaryEntry } from '../../services/diaryService';

interface DiaryCardProps {
  diary: DiaryEntry;
  onSelect: (diary: DiaryEntry) => void;
  onEdit: (diary: DiaryEntry, e: React.MouseEvent) => void;
  onDelete: (diary: DiaryEntry, e: React.MouseEvent) => void;
}

export const DiaryCard: React.FC<DiaryCardProps> = ({
  diary,
  onSelect,
  onEdit,
  onDelete,
}) => {
  return (
    <div
      className="diary-card bg-gradient-to-r from-pink-50 to-purple-50 rounded-xl p-5 shadow-sm hover:shadow-md transition-all cursor-pointer border border-pink-100 relative group"
      onClick={() => onSelect(diary)}
    >
      {/* Action buttons - shown on hover */}
      <div className="absolute top-3 right-3 flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
        <button
          onClick={(e) => onEdit(diary, e)}
          className="p-1.5 bg-blue-500 text-white rounded-lg hover:bg-blue-600 text-sm"
          title="编辑"
        >
          ✏️
        </button>
        <button
          onClick={(e) => onDelete(diary, e)}
          className="p-1.5 bg-red-500 text-white rounded-lg hover:bg-red-600 text-sm"
          title="删除"
        >
          🗑️
        </button>
      </div>

      {/* Date */}
      <div className="flex justify-between items-start mb-3 pr-16">
        <h3 className="font-bold text-gray-800 text-lg flex items-center gap-2">
          <span className="text-2xl">📔</span>
          {diary.date}
        </h3>
        <div className="flex gap-2 flex-wrap">
          {diary.category && (
            <span className="text-xs px-2 py-1 bg-purple-200 text-purple-700 rounded-full font-medium">
              {diary.category}
            </span>
          )}
        </div>
      </div>

      {/* Content preview */}
      <p className="text-gray-700 text-sm leading-relaxed line-clamp-3 whitespace-pre-wrap">
        {diary.content}
      </p>

      {/* Tags */}
      {diary.tags.length > 0 && (
        <div className="mt-3 flex gap-2 flex-wrap">
          {diary.tags.map((tag) => (
            <span
              key={tag}
              className="text-xs px-2 py-1 bg-white text-pink-600 rounded border border-pink-200"
            >
              #{tag}
            </span>
          ))}
        </div>
      )}
    </div>
  );
};
