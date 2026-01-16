/** Character type definitions */

export type CharacterTrait =
  | 'affectionate'
  | 'playful'
  | 'caring'
  | 'opinionated'
  | 'sometimes_jealous'
  | 'proactive'
  | 'shy'
  | 'energetic';

export type CharacterType = 'emotional_companion' | 'mentor' | 'friend';

export interface SpeakingStyle {
  affectionate_markers: string[];
  common_phrases: {
    greeting: string[];
    agreement: string[];
    disagreement: string[];
    concern: string[];
    sharing: string[];
    jealousy: string[];
  };
  tone_variations: {
    very_playful: { marker_frequency: string; sentence_length: string; emoji_use: string };
    normal: { marker_frequency: string; sentence_length: string; emoji_use: string };
    more_mature: { marker_frequency: string; sentence_length: string; emoji_use: string };
  };
}

export interface BehavioralParameters {
  proactivity_level: number;
  jealousy_frequency: number;
  opinionatedness: number;
  emotional_sensitivity: number;
  argument_avoidance_threshold: number;
}

export interface CharacterIdentity {
  role: string;
  age: number;
  personality_traits: CharacterTrait[];
  description: string;
}

export interface CharacterMetadata {
  version: string;
  created_at: string;
  author: string;
  tags: string[];
}

export interface CharacterTemplate {
  character_id: string;
  name: string;
  base_nickname: string;
  character_type: CharacterType;
  identity: CharacterIdentity;
  system_prompt: {
    base: string;
    variables: string[];
  };
  speaking_style: SpeakingStyle;
  behavior: BehavioralParameters;
  conversation_starters: string[];
  examples: Array<{
    context: string;
    user: string;
    assistant: string;
  }>;
  metadata: CharacterMetadata;
}

export interface UserPreference {
  user_id: string;
  character_id: string;
  nickname?: string;
  style_level: number;
  custom_instructions?: string;
  relationship_notes?: string;
  created_at: string;
  updated_at: string;
}
