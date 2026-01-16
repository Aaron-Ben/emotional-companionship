/** API response type definitions */

import { CharacterTemplate, UserPreference } from './character';

export interface ApiResponse<T> {
  data?: T;
  error?: string;
  message?: string;
}

export interface CharacterListResponse {
  characters: CharacterTemplate[];
  count: number;
}

export interface CharacterResponse {
  character: CharacterTemplate;
}

export interface UserPreferenceResponse {
  preference: UserPreference;
}

export interface ConversationStarterRequest {
  character_id?: string;
}

export interface StarterResponse {
  starter: string;
  character_id: string;
  timestamp?: string;
}

export interface UserPreferenceCreate {
  character_id: string;
  nickname?: string;
  style_level?: number;
  custom_instructions?: string;
  relationship_notes?: string;
}

export interface UserPreferenceUpdate {
  character_id: string;
  nickname?: string;
  style_level?: number;
  custom_instructions?: string;
  relationship_notes?: string;
}
