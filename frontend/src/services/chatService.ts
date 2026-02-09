/** Chat API service */

import { API_ENDPOINTS, apiRequest } from './api';
import type { ChatRequest, ChatResponse } from '../types/chat';

interface SendMessageOptions {
  topic_id?: number;
  character_uuid?: string;
}

export async function sendMessage(
  request: ChatRequest,
  options?: SendMessageOptions
): Promise<ChatResponse> {
  const body: Record<string, unknown> = {
    message: request.message,
    character_id: request.character_id,
    conversation_history: request.conversation_history,
    stream: false,
  };

  if (options?.topic_id !== undefined) {
    body.topic_id = options.topic_id;
  }
  if (options?.character_uuid) {
    body.character_uuid = options.character_uuid;
  }

  return apiRequest<ChatResponse>(API_ENDPOINTS.chat(), {
    method: 'POST',
    body: JSON.stringify(body),
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
  request: ChatRequest,
  options?: SendMessageOptions
): AsyncGenerator<string, void, unknown> {
  const body: Record<string, unknown> = {
    message: request.message,
    character_id: request.character_id,
    conversation_history: request.conversation_history,
    stream: true,
  };

  if (options?.topic_id !== undefined) {
    body.topic_id = options.topic_id;
  }
  if (options?.character_uuid) {
    body.character_uuid = options.character_uuid;
  }

  const response = await fetch(API_ENDPOINTS.chatStream(), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
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
