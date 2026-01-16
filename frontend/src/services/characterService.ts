/** Character API service */

import { API_ENDPOINTS, apiRequest } from './api';
import type {
  CharacterListResponse,
  CharacterResponse,
  UserPreferenceResponse,
  StarterResponse,
  UserPreferenceCreate,
} from '../types/api';

export async function listCharacters() {
  return apiRequest<CharacterListResponse>(API_ENDPOINTS.listCharacters());
}

export async function getCharacter(id: string) {
  return apiRequest<CharacterResponse>(API_ENDPOINTS.getCharacter(id));
}

export async function updateUserPreferences(data: UserPreferenceCreate) {
  return apiRequest<UserPreferenceResponse>(API_ENDPOINTS.updatePreferences(), {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export async function getUserPreferences(characterId: string) {
  return apiRequest<UserPreferenceResponse>(API_ENDPOINTS.getPreferences(characterId));
}

export async function deleteUserPreferences(characterId: string) {
  return apiRequest<{ message: string; character_id: string }>(
    API_ENDPOINTS.deletePreferences(characterId),
    { method: 'DELETE' }
  );
}

export async function getConversationStarter(characterId: string) {
  return apiRequest<StarterResponse>(API_ENDPOINTS.getStarter(), {
    method: 'POST',
    body: JSON.stringify(characterId ? { character_id: characterId } : {}),
  });
}
