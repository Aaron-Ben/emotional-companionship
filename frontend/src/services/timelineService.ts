/** Timeline API service */

import { apiRequest } from './api';
import type {
  FutureEvent,
  TimelineDay,
  ExtractTimelineRequest,
  ExtractTimelineResponse,
  GetEventsRequest,
  GetEventsByDateRequest,
  UpdateEventStatusRequest,
  EventsGroupedByDate,
  EventStatus,
} from '../types/timeline';

// Add timeline endpoints to API_ENDPOINTS
const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export const TIMELINE_ENDPOINTS = {
  extract: () => `${API_BASE}/api/v1/timeline/extract`,
  events: () => `${API_BASE}/api/v1/timeline/events`,
  eventsByDate: () => `${API_BASE}/api/v1/timeline/events/by-date`,
  updateStatus: (id: string) => `${API_BASE}/api/v1/timeline/events/${id}/status`,
  deleteEvent: (id: string) => `${API_BASE}/api/v1/timeline/events/${id}`,
};

/**
 * Extract timeline events from conversation
 */
export async function extractTimeline(request: ExtractTimelineRequest): Promise<ExtractTimelineResponse> {
  return apiRequest<ExtractTimelineResponse>(TIMELINE_ENDPOINTS.extract(), {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

/**
 * Get future events for a user and character
 */
export async function getFutureEvents(params: GetEventsRequest): Promise<EventsGroupedByDate> {
  const { character_id, user_id, days_ahead = 30, status } = params;

  const url = new URL(TIMELINE_ENDPOINTS.events());
  url.searchParams.append('character_id', character_id);
  url.searchParams.append('user_id', user_id);
  url.searchParams.append('days_ahead', String(days_ahead));
  if (status) {
    url.searchParams.append('status', status);
  }

  const response = await fetch(url.toString());
  if (!response.ok) {
    throw new Error(`API Error: ${response.status}`);
  }
  return response.json();
}

/**
 * Get events for a specific date
 */
export async function getEventsByDate(request: GetEventsByDateRequest): Promise<FutureEvent[]> {
  return apiRequest<FutureEvent[]>(TIMELINE_ENDPOINTS.eventsByDate(), {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

/**
 * Update event status
 */
export async function updateEventStatus(
  eventId: string,
  request: UpdateEventStatusRequest
): Promise<{ id: string; status: string; updated_at: string }> {
  return apiRequest(TIMELINE_ENDPOINTS.updateStatus(eventId), {
    method: 'PUT',
    body: JSON.stringify(request),
  });
}

/**
 * Delete an event
 */
export async function deleteEvent(eventId: string): Promise<{ message: string; id: string }> {
  return apiRequest(TIMELINE_ENDPOINTS.deleteEvent(eventId), {
    method: 'DELETE',
  });
}

/**
 * Group events by date and convert to TimelineDay format
 */
export function groupEventsByDate(events: FutureEvent[]): TimelineDay[] {
  const grouped: Record<string, FutureEvent[]> = {};

  for (const event of events) {
    if (!grouped[event.event_date]) {
      grouped[event.event_date] = [];
    }
    grouped[event.event_date].push(event);
  }

  const days: TimelineDay[] = [];
  for (const [date, eventsList] of Object.entries(grouped)) {
    days.push({
      date,
      displayDate: formatDisplayDate(date),
      events: eventsList,
      eventCount: eventsList.length,
      expanded: false,
    });
  }

  // Sort by date
  days.sort((a, b) => a.date.localeCompare(b.date));

  return days;
}

/**
 * Convert API response (grouped by display date) to TimelineDay format
 */
export function convertApiResponseToTimelineDays(
  response: EventsGroupedByDate
): TimelineDay[] {
  const days: TimelineDay[] = [];

  for (const [displayDate, eventsList] of Object.entries(response)) {
    if (eventsList.length > 0) {
      const firstEvent = eventsList[0];
      days.push({
        date: firstEvent.event_date,
        displayDate,
        events: eventsList,
        eventCount: eventsList.length,
        expanded: false,
      });
    }
  }

  // Sort by date
  days.sort((a, b) => a.date.localeCompare(b.date));

  return days;
}

/**
 * Format date for display (1月26日 周一)
 */
export function formatDisplayDate(dateStr: string): string {
  const date = new Date(dateStr);
  const month = date.getMonth() + 1;
  const day = date.getDate();
  const weekdays = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'];
  const weekday = weekdays[date.getDay()];

  return `${month}月${day}日 ${weekday}`;
}

/**
 * Get status label for display
 */
export function getStatusLabel(status: EventStatus): string {
  const labels: Record<EventStatus, string> = {
    pending: '待处理',
    completed: '已完成',
    cancelled: '已取消',
  };
  return labels[status] || status;
}

/**
 * Get status color for display
 */
export function getStatusColor(status: EventStatus): string {
  const colors: Record<EventStatus, string> = {
    pending: '#60a5fa',    // 蓝色
    completed: '#4CAF50',  // 绿色
    cancelled: '#EF4444',  // 红色
  };
  return colors[status] || '#999999';
}

export default {
  extractTimeline,
  getFutureEvents,
  getEventsByDate,
  updateEventStatus,
  deleteEvent,
  groupEventsByDate,
  convertApiResponseToTimelineDays,
  formatDisplayDate,
  getStatusLabel,
  getStatusColor,
};
