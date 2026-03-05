/** Character API service - Simplified for file system based storage */

import { API_ENDPOINTS, apiRequest } from './api';
import type {
  CreateCharacterRequest,
  UpdateCharacterPromptRequest,
  UserCharacterListResponse,
  UserCharacterResponse,
} from '../types/api';
import type { UserCharacter } from '../types/character';

// User character management functions

export async function createCharacter(data: CreateCharacterRequest): Promise<UserCharacterResponse> {
  return apiRequest<UserCharacterResponse>(API_ENDPOINTS.createCharacter(), {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function listUserCharacters(): Promise<UserCharacterListResponse> {
  return apiRequest<UserCharacterListResponse>(API_ENDPOINTS.listUserCharacters());
}

export async function getUserCharacter(id: string): Promise<UserCharacterResponse> {
  return apiRequest<UserCharacterResponse>(API_ENDPOINTS.getUserCharacter(id));
}

export async function deleteUserCharacter(id: string): Promise<{ message: string; character_id: string }> {
  return apiRequest<{ message: string; character_id: string }>(
    API_ENDPOINTS.deleteUserCharacter(id),
    { method: 'DELETE' }
  );
}

export async function updateCharacterPrompt(
  id: string,
  data: UpdateCharacterPromptRequest
): Promise<UserCharacterResponse> {
  return apiRequest<UserCharacterResponse>(API_ENDPOINTS.updateUserCharacterPrompt(id), {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

export async function listAllCharacters(): Promise<UserCharacter[]> {
  try {
    const response = await listUserCharacters();
    return response.characters;
  } catch (error) {
    console.error('Failed to load characters:', error);
    return [];
  }
}
