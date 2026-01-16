/** Chat API service */

import { API_ENDPOINTS, apiRequest } from './api';
import type { ChatRequest, ChatResponse } from '../types/chat';

export async function sendMessage(request: ChatRequest): Promise<ChatResponse> {
  return apiRequest<ChatResponse>(API_ENDPOINTS.chat(), {
    method: 'POST',
    body: JSON.stringify({
      message: request.message,
      character_id: request.character_id,
      conversation_history: request.conversation_history,
      stream: false,
    }),
  });
}

export async function getChatStarter(characterId: string = 'sister_001') {
  return apiRequest<{ starter: string; character_id: string; timestamp: string }>(
    API_ENDPOINTS.chatStarter(),
    {
      method: 'POST',
      body: JSON.stringify({ character_id: characterId }),
    }
  );
}

/**
 * Send a message with streaming response
 * Returns an async generator that yields chunks of the response
 */
export async function* sendMessageStream(
  request: ChatRequest
): AsyncGenerator<string, void, unknown> {
  const response = await fetch(API_ENDPOINTS.chatStream(), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      message: request.message,
      character_id: request.character_id,
      conversation_history: request.conversation_history,
      stream: true,
    }),
  });

  if (!response.ok) {
    throw new Error(`Stream error: ${response.status}`);
  }

  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error('No reader available');
  }

  const decoder = new TextDecoder();

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value);
      const lines = chunk.split('\n');

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6);
          if (data === '[DONE]') return;
          if (data.startsWith('[ERROR')) {
            throw new Error(data.slice(7));
          }
          yield data;
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}
