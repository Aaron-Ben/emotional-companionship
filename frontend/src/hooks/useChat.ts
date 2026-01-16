/** Custom hook for chat functionality */

import { useState, useCallback, useRef } from 'react';
import { sendMessage, sendMessageStream, getChatStarter } from '../services/chatService';
import type { DisplayMessage, ChatRequest, Message } from '../types/chat';

const DEFAULT_CHARACTER_ID = 'sister_001';
const STORAGE_KEY = 'chat_history';

export function useChat(characterId: string = DEFAULT_CHARACTER_ID) {
  const [messages, setMessages] = useState<DisplayMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [streamingMessage, setStreamingMessage] = useState('');
  const errorRef = useRef<string | null>(null);

  // Load history from localStorage on mount
  useState(() => {
    try {
      const stored = localStorage.getItem(`${STORAGE_KEY}_${characterId}`);
      if (stored) {
        const parsed = JSON.parse(stored);
        setMessages(parsed.map((msg: any) => ({
          ...msg,
          timestamp: new Date(msg.timestamp),
        })));
      }
    } catch (err) {
      console.error('Failed to load chat history:', err);
    }
  });

  // Save to localStorage whenever messages change
  const saveHistory = useCallback((newMessages: DisplayMessage[]) => {
    try {
      localStorage.setItem(
        `${STORAGE_KEY}_${characterId}`,
        JSON.stringify(newMessages)
      );
    } catch (err) {
      console.error('Failed to save chat history:', err);
    }
  }, [characterId]);

  const addMessage = useCallback((message: DisplayMessage) => {
    setMessages((prev) => {
      const newMessages = [...prev, message];
      saveHistory(newMessages);
      return newMessages;
    });
  }, [saveHistory]);

  const send = useCallback(async (content: string) => {
    if (!content.trim() || loading) return;

    setLoading(true);
    errorRef.current = null;

    // Add user message
    const userMessage: DisplayMessage = {
      id: `user-${Date.now()}`,
      content: content.trim(),
      isUser: true,
      timestamp: new Date(),
    };
    addMessage(userMessage);

    // Build conversation history for API
    const conversationHistory: Message[] = messages
      .slice(-10) // Last 10 messages for context
      .map((msg) => ({
        role: msg.isUser ? 'user' : 'assistant',
        content: msg.content,
      }));

    const request: ChatRequest = {
      message: content,
      character_id: characterId,
      conversation_history: conversationHistory,
    };

    try {
      const response = await sendMessage(request);

      const assistantMessage: DisplayMessage = {
        id: `assistant-${Date.now()}`,
        content: response.message,
        isUser: false,
        timestamp: new Date(response.timestamp),
        emotion: response.emotion_detected,
      };
      addMessage(assistantMessage);
    } catch (err) {
      errorRef.current = err instanceof Error ? err.message : 'Failed to send message';
    } finally {
      setLoading(false);
    }
  }, [messages, characterId, loading, addMessage]);

  const sendStream = useCallback(async (content: string) => {
    if (!content.trim() || loading) return;

    setLoading(true);
    errorRef.current = null;
    setStreamingMessage('');

    // Add user message
    const userMessage: DisplayMessage = {
      id: `user-${Date.now()}`,
      content: content.trim(),
      isUser: true,
      timestamp: new Date(),
    };
    addMessage(userMessage);

    // Build conversation history
    const conversationHistory: Message[] = messages
      .slice(-10)
      .map((msg) => ({
        role: msg.isUser ? 'user' : 'assistant',
        content: msg.content,
      }));

    const request: ChatRequest = {
      message: content,
      character_id: characterId,
      conversation_history: conversationHistory,
    };

    // Create placeholder for streaming message
    const streamingId = `streaming-${Date.now()}`;
    setMessages((prev) => [...prev, {
      id: streamingId,
      content: '',
      isUser: false,
      timestamp: new Date(),
    }]);

    try {
      let fullResponse = '';
      for await (const chunk of sendMessageStream(request)) {
        fullResponse += chunk;
        setStreamingMessage(fullResponse);
        setMessages((prev) => prev.map((msg) =>
          msg.id === streamingId
            ? { ...msg, content: fullResponse }
            : msg
        ));
      }

      // Finalize the message
      setMessages((prev) => prev.map((msg) =>
        msg.id === streamingId
          ? { ...msg, id: `assistant-${Date.now()}` }
          : msg
      ));

      saveHistory(messages);
    } catch (err) {
      errorRef.current = err instanceof Error ? err.message : 'Failed to send message';
      // Remove the streaming message placeholder
      setMessages((prev) => prev.filter((msg) => msg.id !== streamingId));
    } finally {
      setLoading(false);
      setStreamingMessage('');
    }
  }, [messages, characterId, loading, addMessage, saveHistory]);

  const clearHistory = useCallback(() => {
    setMessages([]);
    localStorage.removeItem(`${STORAGE_KEY}_${characterId}`);
  }, [characterId]);

  const getStarter = useCallback(async () => {
    try {
      const data = await getChatStarter(characterId);
      return data.starter;
    } catch (err) {
      console.error('Failed to get conversation starter:', err);
      return null;
    }
  }, [characterId]);

  return {
    messages,
    loading,
    error: errorRef.current,
    streamingMessage,
    send,
    sendStream,
    clearHistory,
    getStarter,
  };
}
