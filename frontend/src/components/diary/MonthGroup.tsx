/** Month group component for displaying diaries grouped by month */

import React from 'react';
import { DiaryGroup, DiaryEntry } from '../../services/diaryService';
import { DiaryCard } from './DiaryCard';

interface MonthGroupProps {
  group: DiaryGroup;
  onToggle: () => void;
  onSelectDiary: (diary: DiaryEntry) => void;
  onEditDiary: (diary: DiaryEntry, e: React.MouseEvent) => void;
  onDeleteDiary: (diary: DiaryEntry, e: React.MouseEvent) => void;
}

export const MonthGroup: React.FC<MonthGroupProps> = ({
  group,
  onToggle,
  onSelectDiary,
  onEditDiary,
  onDeleteDiary,
}) => {
  const hasImportantDiary = group.diaries.some((d) => d.tags.includes('重要时刻'));

  return (
    <div id={`month-${group.year}-${group.month}`} className="month-group">
      {/* Month header */}
      <div
        className={`month-header ${group.expanded ? 'expanded' : ''}`}
        onClick={onToggle}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-xl">{group.expanded ? '▼' : '▶'}</span>
            <span className="text-lg font-bold">{group.monthLabel}</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-sm opacity-75">{group.count}篇日记</span>
            {hasImportantDiary && <span className="text-yellow-400">⭐</span>}
          </div>
        </div>
      </div>

      {/* Diary list wrapper with animation */}
      <div
        className={`diary-list-wrapper ${group.expanded ? 'expanded' : 'collapsed'}`}
      >
        <div className="diary-list">
          {group.diaries
            .sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime())
            .map((diary) => (
              <DiaryCard
                key={diary.id}
                diary={diary}
                onSelect={onSelectDiary}
                onEdit={onEditDiary}
                onDelete={onDeleteDiary}
              />
            ))}
        </div>
      </div>
    </div>
  );
};
