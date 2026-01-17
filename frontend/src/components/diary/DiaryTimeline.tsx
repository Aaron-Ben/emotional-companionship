/** Diary timeline component with month navigation and grouping */

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
      <div className="text-center text-gray-400 py-8">
        <p className="text-lg mb-2">还没有日记呢～</p>
        <p className="text-sm">妹妹会记录和哥哥的重要时刻</p>
      </div>
    );
  }

  return (
    <div className="diary-timeline-container">
      {/* Side navigation */}
      <div className="month-nav">
        {groups.map((group) => (
          <div
            key={`${group.year}-${group.month}`}
            className={`month-nav-item ${
              activeMonth === `${group.year}-${group.month}` ? 'active' : ''
            }`}
            onClick={() => scrollToMonth(group.year, group.month)}
          >
            <div className="text-sm font-medium">
              {group.year}年{group.month}月
            </div>
            <div className="text-xs opacity-75">{group.count}篇</div>
          </div>
        ))}
      </div>

      {/* Timeline content */}
      <div className="diary-timeline-content">
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
