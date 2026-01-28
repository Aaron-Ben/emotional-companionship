/** TTS (Text-to-Speech) service */

import { API_ENDPOINTS, apiRequest } from './api';
import type { TTSRequest, TTSResponse } from '../types/chat';

/**
 * Convert text to speech
 * @returns TTS response with audio path
 */
export async function textToSpeech(request: TTSRequest): Promise<TTSResponse> {
  return apiRequest<TTSResponse>(API_ENDPOINTS.tts(), {
    method: 'POST',
    body: JSON.stringify({
      text: request.text,
      engine: request.engine || 'genie',
      character_id: request.character_id || 'sister_001',
    }),
  });
}

/**
 * Get audio URL from TTS response
 */
export function getAudioUrl(audioPath: string): string {
  // audioPath is like "/api/v1/chat/tts/audio/tts_abc12345.wav"
  // We need to convert it to full URL
  const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
  return audioPath.startsWith('http') ? audioPath : `${API_BASE_URL}${audioPath}`;
}

/**
 * Play TTS audio
 * @param audioPath - Path to audio file
 * @returns Promise that resolves when audio finishes playing
 */
export function playTTSAudio(audioPath: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const audio = new Audio(getAudioUrl(audioPath));

    audio.onended = () => resolve();
    audio.onerror = (error) => reject(error);

    audio.play().catch(reject);
  });
}

/**
 * Synthesize and play TTS in one call
 */
export async function speakText(
  text: string,
  engine: 'genie' = 'genie',
  characterId: string = 'sister_001'
): Promise<void> {
  const response = await textToSpeech({
    text,
    engine,
    character_id: characterId,
  });

  if (!response.success || !response.audio_path) {
    throw new Error(response.error || 'TTS synthesis failed');
  }

  await playTTSAudio(response.audio_path);
}
