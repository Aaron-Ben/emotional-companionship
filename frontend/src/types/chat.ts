/** Chat type definitions */

export type EmotionType = 'happy' | 'sad' | 'angry' | 'neutral' | 'excited' | 'frustrated';

export interface EmotionState {
  primary_emotion: EmotionType;
  confidence: number;
  intensity: number;
}

export interface MessageContext {
  user_mood?: EmotionState;
  recent_conversation_summary?: string;
  character_state: Record<string, unknown>;
  should_avoid_argument: boolean;
  initiate_topic: boolean;
}

export type MessageRole = 'system' | 'user' | 'assistant';

export interface Message {
  role: MessageRole;
  content: string;
  timestamp?: string;
}

export interface ChatRequest {
  message: string;
  character_id: string;
  conversation_history?: Message[];
  stream?: boolean;
}

export interface ChatResponse {
  message: string;
  character_id: string;
  context_used?: MessageContext;
  emotion_detected?: EmotionState;
  timestamp: string;
}

export interface DisplayMessage {
  id: string;
  content: string;
  isUser: boolean;
  timestamp: Date;
  emotion?: EmotionState;
}

export interface ConversationHistory {
  messages: DisplayMessage[];
  characterId: string;
  lastUpdated: Date;
}

// RPG game dialogue style types
export type DialoguePhase = 'user_input' | 'ai_reply' | 'completed';

export interface CurrentTurn {
  phase: DialoguePhase;
  userMessage: string;
  aiMessage: string;
  timestamp: Date;
}

// Voice input types
export interface VoiceInputOptions {
  characterId?: string;
}

export interface VoiceRecognitionResult {
  text: string;
  emotion?: string;
  event?: string;
  success: boolean;
  error?: string;
}

export interface VoiceChatOptions extends VoiceInputOptions {
  conversationHistory?: Message[];
  stream?: boolean;
}

export type RecordingState = 'idle' | 'recording' | 'processing';

// TTS types
export interface TTSRequest {
  text: string;
  engine?: 'vits' | 'pyttsx3';
  character_id?: string;
}

export interface TTSResponse {
  success: boolean;
  audio_path?: string;
  error?: string;
  engine: string;
}
