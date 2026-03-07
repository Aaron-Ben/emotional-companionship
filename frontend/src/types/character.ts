/** Character type definitions - Simplified for file system based storage */

// User-created character - Main character model
// character_id IS the UUID4
export interface Character {
  character_id: string;  // UUID4
  name: string;
  created_at: string;
  updated_at: string;
}

// Backward compatibility alias
export type UserCharacter = Character;
