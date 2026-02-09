/** Diary timeline component with month navigation and grouping - Refined elegant style */

import React, { useState, useEffect } from 'react';
import { DiaryEntry, DiaryGroup } from '../../services/diaryService';
import { MonthGroup } from './MonthGroup';

interface DiaryTimelineProps {
  diaries: DiaryEntry[];
  onSelectDiary: (diary: DiaryEntry) => void;
  onEditDiary: (diary: DiaryEntry, e: React.MouseEvent) => void;
  onDeleteDiary: (diary: DiaryEntry, e: React.MouseEvent) => void;
}

export const DiaryTimeline: React.FC<DiaryTimelineProps> = ({
  diaries,
  onSelectDiary,
  onEditDiary,
  onDeleteDiary,
}) => {
  const [groups, setGroups] = useState<DiaryGroup[]>([]);
  const [activeMonth, setActiveMonth] = useState<string>('');

  // Initialize groups when diaries change
  useEffect(() => {
    // Import here to avoid circular dependency
    import('../../services/diaryService').then(({ groupDiariesByMonth }) => {
      const grouped = groupDiariesByMonth(diaries);
      setGroups(grouped);
      if (grouped.length > 0) {
        setActiveMonth(`${grouped[0].year}-${grouped[0].month}`);
      }
    });
  }, [diaries]);

  // Toggle expand/collapse for a group
  const toggleGroup = (index: number) => {
    setGroups((prev) =>
      prev.map((group, i) =>
        i === index ? { ...group, expanded: !group.expanded } : group
      )
    );
  };

  // Scroll to specific month
  const scrollToMonth = (year: number, month: number) => {
    const key = `${year}-${month}`;
    setActiveMonth(key);

    // Expand that month
    setGroups((prev) =>
      prev.map((group) =>
        group.year === year && group.month === month
          ? { ...group, expanded: true }
          : group
      )
    );

    // Scroll to element
    const element = document.getElementById(`month-${key}`);
    element?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  if (groups.length === 0) {
    return (
      <div className="text-center text-neutral-400 dark:text-neutral-500 py-8">
        <p className="text-lg mb-2">还没有日记呢～</p>
        <p className="text-sm">妹妹会记录和哥哥的重要时刻</p>
      </div>
    );
  }

  return (
    <div className="flex gap-5 items-start">
      {/* Side navigation */}
      <div className="sticky top-4 w-32 flex-shrink-0 max-h-[calc(80vh-32px)] overflow-y-auto">
        <div className="bg-white dark:bg-neutral-800 rounded-2xl border border-neutral-200 dark:border-neutral-700 p-2 shadow-sm">
          {groups.map((group) => (
            <div
              key={`${group.year}-${group.month}`}
              className={`
                px-3 py-2 rounded-xl cursor-pointer transition-all duration-200 text-sm mb-1 last:mb-0
                ${activeMonth === `${group.year}-${group.month}`
                  ? 'bg-gradient-to-r from-rose-400 to-rose-500 text-white shadow-sm font-medium'
                  : 'text-neutral-600 dark:text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-700'
                }
              `}
              onClick={() => scrollToMonth(group.year, group.month)}
            >
              <div className="text-xs font-medium">
                {group.year}年{group.month}月
              </div>
              <div className={clsx(
                'text-[10px]',
                activeMonth === `${group.year}-${group.month}` ? 'text-white/70' : 'text-neutral-400'
              )}>
                {group.count}篇
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Timeline content */}
      <div className="flex-1 min-w-0">
        {groups.map((group, index) => (
          <MonthGroup
            key={`${group.year}-${group.month}`}
            group={group}
            onToggle={() => toggleGroup(index)}
            onSelectDiary={onSelectDiary}
            onEditDiary={onEditDiary}
            onDeleteDiary={onDeleteDiary}
          />
        ))}
      </div>
    </div>
  );
};

// Helper for clsx
function clsx(...classes: (string | boolean | undefined | null)[]) {
  return classes.filter(Boolean).join(' ');
}
