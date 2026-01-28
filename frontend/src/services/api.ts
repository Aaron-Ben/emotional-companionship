/** API base configuration */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export const API_ENDPOINTS = {
  // Character endpoints
  listCharacters: () => `${API_BASE_URL}/api/v1/character/`,
  getCharacter: (id: string) => `${API_BASE_URL}/api/v1/character/${id}`,
  updatePreferences: () => `${API_BASE_URL}/api/v1/character/preferences`,
  getPreferences: (id: string) => `${API_BASE_URL}/api/v1/character/preferences/${id}`,
  deletePreferences: (id: string) => `${API_BASE_URL}/api/v1/character/preferences/${id}`,
  getStarter: () => `${API_BASE_URL}/api/v1/character/starter`,

  // Chat endpoints
  chat: () => `${API_BASE_URL}/api/v1/chat/`,
  chatStream: () => `${API_BASE_URL}/api/v1/chat/stream`,
  chatStarter: () => `${API_BASE_URL}/api/v1/chat/starter`,
  voiceInput: () => `${API_BASE_URL}/api/v1/chat/voice`,
  voiceChat: () => `${API_BASE_URL}/api/v1/chat/voice/chat`,

  // TTS endpoints
  tts: () => `${API_BASE_URL}/api/v1/chat/tts`,
  ttsAudio: (filename: string) => `${API_BASE_URL}/api/v1/chat/tts/audio/${filename}`,
} as const;

export async function apiRequest<T>(
  url: string,
  options: RequestInit = {}
): Promise<T> {
  const defaultHeaders: HeadersInit = {
    'Content-Type': 'application/json',
  };

  const response = await fetch(url, {
    ...options,
    headers: {
      ...defaultHeaders,
      ...options.headers,
    },
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`API Error: ${response.status} - ${errorText}`);
  }

  return response.json();
}

export default API_BASE_URL;
