/** Character type definitions - Simplified for file system based storage */

// User-created character - Main character model
// character_id IS the UUID
export interface UserCharacter {
  character_id: string;  // UUID4
  name: string;
  created_at: string;
}
