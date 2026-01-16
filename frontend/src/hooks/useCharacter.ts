/** Custom hook for character management */

import { useState, useEffect, useCallback } from 'react';
import { getCharacter, listCharacters, getConversationStarter } from '../services/characterService';
import type { CharacterTemplate } from '../types/character';

export function useCharacter(characterId: string) {
  const [character, setCharacter] = useState<CharacterTemplate | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchCharacter = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const data = await getCharacter(characterId);
      setCharacter(data.character);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load character');
    } finally {
      setLoading(false);
    }
  }, [characterId]);

  useEffect(() => {
    fetchCharacter();
  }, [fetchCharacter]);

  const getStarter = useCallback(async () => {
    try {
      const data = await getConversationStarter(characterId);
      return data.starter;
    } catch (err) {
      console.error('Failed to get conversation starter:', err);
      return null;
    }
  }, [characterId]);

  return { character, loading, error, refetch: fetchCharacter, getStarter };
}

export function useCharacters() {
  const [characters, setCharacters] = useState<CharacterTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchAll() {
      setLoading(true);
      setError(null);

      try {
        const data = await listCharacters();
        setCharacters(data.characters);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load characters');
      } finally {
        setLoading(false);
      }
    }

    fetchAll();
  }, []);

  return { characters, loading, error };
}
