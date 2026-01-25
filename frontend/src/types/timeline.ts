/** Timeline type definitions */

export type TimeExpressionType =
  | 'relative_day'      // 明天, 后天, 3天后
  | 'relative_week'     // 下周, 下下周
  | 'relative_month'    // 下个月, 明年
  | 'specific_date'     // 1月25日, 2月14日
  | 'fuzzy_time';       // 一会, 改天, 以后

export type EventStatus = 'pending' | 'completed' | 'cancelled';

export interface FutureEvent {
  id?: string;
  character_id: string;
  user_id: string;
  title: string;
  description?: string;
  event_date: string;           // YYYY-MM-DD
  original_expression: string;  // 原始时间表达
  expression_type: TimeExpressionType;
  confidence: number;           // 0-1
  source_conversation?: string;
  tags: string[];
  status: EventStatus;
  created_at?: string;
  updated_at?: string;
}

export interface TimelineDay {
  date: string;              // YYYY-MM-DD
  displayDate: string;       // 1月26日 周一
  events: FutureEvent[];
  eventCount: number;
  expanded: boolean;         // For UI state
}

export interface TimelineWeek {
  weekNumber: number;
  startDate: string;
  endDate: string;
  days: TimelineDay[];
}

export interface ExtractTimelineRequest {
  character_id: string;
  user_id: string;
  conversation_messages: Array<{ role: string; content: string }>;
}

export interface ExtractTimelineResponse {
  events_extracted: number;
  events: FutureEvent[];
}

export interface GetEventsRequest {
  character_id: string;
  user_id: string;
  days_ahead?: number;
  status?: EventStatus;
}

export interface GetEventsByDateRequest {
  character_id: string;
  user_id: string;
  date: string;  // YYYY-MM-DD
}

export interface UpdateEventStatusRequest {
  status: EventStatus;
}

// API Response types
export interface EventsGroupedByDate {
  [displayDate: string]: FutureEvent[];
}
