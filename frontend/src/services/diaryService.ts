/** Diary service for managing character diary entries */

export interface DiaryEntry {
  id: string;
  character_id: string;
  user_id: string;
  date: string;
  content: string;
  category: string;
  tags: string[];
  created_at: string;
  updated_at?: string;
}

/** Diary group by month for timeline display */
export interface DiaryGroup {
  year: number;
  month: number;
  monthLabel: string; // "2026年1月"
  diaries: DiaryEntry[];
  count: number;
  expanded: boolean; // UI state: whether this group is expanded
}

/** Map key format: "year-month" e.g., "2026-1" */
export type DiaryGroupMap = Record<string, DiaryEntry[]>;

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export async function listDiaries(characterId: string = 'sister_001', limit: number = 10): Promise<DiaryEntry[]> {
  const response = await fetch(`${API_BASE}/api/v1/diary/list?character_id=${characterId}&limit=${limit}`);

  if (!response.ok) {
    throw new Error(`Failed to list diaries: ${response.statusText}`);
  }

  return response.json();
}

export async function getLatestDiary(characterId: string = 'sister_001'): Promise<DiaryEntry | null> {
  const response = await fetch(`${API_BASE}/api/v1/diary/latest?character_id=${characterId}`);

  if (!response.ok) {
    throw new Error(`Failed to get latest diary: ${response.statusText}`);
  }

  return response.json();
}

export async function getDiaryById(diaryId: string): Promise<DiaryEntry> {
  const response = await fetch(`${API_BASE}/api/v1/diary/${diaryId}`);

  if (!response.ok) {
    throw new Error(`Failed to get diary: ${response.statusText}`);
  }

  return response.json();
}

export async function generateDiary(data: {
  character_id: string;
  conversation_summary: string;
  trigger_type: string;
}): Promise<{ diary: DiaryEntry; message: string }> {
  const response = await fetch(`${API_BASE}/api/v1/diary/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    throw new Error(`Failed to generate diary: ${response.statusText}`);
  }

  return response.json();
}

export async function updateDiary(
  diaryId: string,
  data: {
    content: string;
    tags: string[];
  }
): Promise<{ diary: DiaryEntry; message: string }> {
  const response = await fetch(`${API_BASE}/api/v1/diary/${diaryId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    throw new Error(`Failed to update diary: ${response.statusText}`);
  }

  return response.json();
}

export async function deleteDiary(diaryId: string): Promise<{ message: string; diary_id: string }> {
  const response = await fetch(`${API_BASE}/api/v1/diary/${diaryId}`, {
    method: 'DELETE',
  });

  if (!response.ok) {
    throw new Error(`Failed to delete diary: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Group diaries by month for timeline display
 * @param diaries - Array of diary entries to group
 * @returns Array of diary groups sorted by date (newest first)
 */
export function groupDiariesByMonth(diaries: DiaryEntry[]): DiaryGroup[] {
  const groupMap: DiaryGroupMap = {};

  diaries.forEach((diary) => {
    const date = new Date(diary.date);
    const year = date.getFullYear();
    const month = date.getMonth() + 1; // 1-12
    const key = `${year}-${month}`;

    if (!groupMap[key]) {
      groupMap[key] = [];
    }
    groupMap[key].push(diary);
  });

  // Convert to array and sort by date (newest first)
  const groups: DiaryGroup[] = Object.entries(groupMap)
    .map(([key, diaries]) => {
      const [year, month] = key.split('-').map(Number);
      return {
        year,
        month,
        monthLabel: `${year}年${month}月`,
        diaries,
        count: diaries.length,
        expanded: false, // Default collapsed
      };
    })
    .sort((a, b) => {
      // Sort descending: newest month first
      if (a.year !== b.year) return b.year - a.year;
      return b.month - a.month;
    });

  // Expand the first (newest) group by default
  if (groups.length > 0) {
    groups[0].expanded = true;
  }

  return groups;
}
