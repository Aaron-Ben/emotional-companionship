/** Diary service for managing character diary entries */

export interface DiaryEntry {
  id: string;
  character_id: string;
  user_id: string;
  date: string;
  content: string;
  trigger_type: string;
  emotions: string[];
  tags: string[];
  created_at: string;
  updated_at?: string;
}

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

export async function generateDiary(data: {
  character_id: string;
  conversation_summary: string;
  trigger_type: string;
  emotions: string[];
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
