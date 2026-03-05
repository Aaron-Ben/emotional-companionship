/** API response type definitions - Simplified for file system based storage */

import { UserCharacter } from './character';

export interface ApiResponse<T> {
  data?: T;
  error?: string;
  message?: string;
}

// User character management types
export interface CreateCharacterRequest {
  name: string;
  prompt: string;
}

export interface UpdateCharacterPromptRequest {
  prompt: string;
}

export interface UserCharacterListResponse {
  characters: UserCharacter[];
  count: number;
}

export interface UserCharacterResponse {
  character: UserCharacter;
}
