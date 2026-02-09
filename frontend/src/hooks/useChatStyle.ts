/** Custom hook for managing chat style preference */

import { useState, useCallback } from 'react';

export type ChatStyle = 'rpg' | 'traditional';

const STORAGE_KEY = 'chat_style';

export function useChatStyle() {
  const [style, setStyle] = useState<ChatStyle>(() => {
    // Load from localStorage, default to 'rpg'
    if (typeof window === 'undefined') return 'rpg';

    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      return (saved === 'traditional' || saved === 'rpg') ? saved : 'rpg';
    } catch {
      return 'rpg';
    }
  });

  const toggleStyle = useCallback(() => {
    setStyle(prev => {
      const newStyle = prev === 'rpg' ? 'traditional' : 'rpg';
      try {
        localStorage.setItem(STORAGE_KEY, newStyle);
      } catch (err) {
        console.error('Failed to save chat style preference:', err);
      }
      return newStyle;
    });
  }, []);

  const setStyleDirect = useCallback((newStyle: ChatStyle) => {
    setStyle(() => {
      try {
        localStorage.setItem(STORAGE_KEY, newStyle);
      } catch (err) {
        console.error('Failed to save chat style preference:', err);
      }
      return newStyle;
    });
  }, []);

  return { style, toggleStyle, setStyle: setStyleDirect };
}
