/** Month group component for displaying diaries grouped by month - Refined elegant style */

import React from 'react';
import { DiaryGroup, DiaryEntry, extractDateFromPath } from '../../services/diaryService';
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
  return (
    <div id={`month-${group.year}-${group.month}`} className="mb-6 animate-fade-in">
      {/* Month header */}
      <div
        className={`
          flex items-center justify-between px-4 py-3 mb-3 rounded-2xl cursor-pointer transition-all duration-200 select-none
          ${group.expanded
            ? 'bg-gradient-to-r from-rose-400 to-rose-500 text-white shadow-sm'
            : 'bg-white dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300 border border-neutral-200 dark:border-neutral-700 hover:border-rose-200 dark:hover:border-rose-800'
          }
        `}
        onClick={onToggle}
      >
        <div className="flex items-center gap-3">
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
            className={clsx('transition-transform duration-200', group.expanded ? 'rotate-90' : '')}
          >
            <path d="M9 18l6-6-6-6"/>
          </svg>
          <span className="font-semibold">{group.monthLabel}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className={clsx(
            'text-sm',
            group.expanded ? 'text-white/80' : 'text-neutral-400'
          )}>
            {group.count}篇日记
          </span>
        </div>
      </div>

      {/* Diary list wrapper with animation */}
      <div
        className={`
          overflow-hidden transition-all duration-300 ease-out
          ${group.expanded ? 'max-h-[5000px] opacity-100' : 'max-h-0 opacity-0'}
        `}
      >
        <div>
          {group.diaries
            .sort((a, b) => extractDateFromPath(b.path).getTime() - extractDateFromPath(a.path).getTime())
            .map((diary) => (
              <DiaryCard
                key={diary.path}
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

// Helper for clsx
function clsx(...classes: (string | boolean | undefined | null)[]) {
  return classes.filter(Boolean).join(' ');
}
