/** Future Timeline Component - Displays future events in expandable nodes */

import React, { useState, useEffect } from 'react';
import type { TimelineDay, FutureEvent } from '../../types/timeline';
import { formatDisplayDate, getStatusLabel, getStatusColor, getFutureEvents } from '../../services/timelineService';
import './FutureTimeline.css';

interface FutureTimelineProps {
  characterId: string;
  userId?: string;
  daysAhead?: number;
  onEventClick?: (event: FutureEvent) => void;
}

export const FutureTimeline: React.FC<FutureTimelineProps> = ({
  characterId,
  userId = 'user_default',
  daysAhead = 30,
  onEventClick,
}) => {
  const [timelineDays, setTimelineDays] = useState<TimelineDay[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedDates, setExpandedDates] = useState<Set<string>>(new Set());

  useEffect(() => {
    loadTimeline();
  }, [characterId, daysAhead]);

  const loadTimeline = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await getFutureEvents({
        character_id: characterId,
        user_id: userId,
        days_ahead: daysAhead,
      });

      // Convert API response to TimelineDay format
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

      setTimelineDays(days);

      if (days.length === 0) {
        setError('暂无未来事件');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载时间线失败');
    } finally {
      setLoading(false);
    }
  };

  const toggleExpand = (date: string) => {
    setExpandedDates((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(date)) {
        newSet.delete(date);
      } else {
        newSet.add(date);
      }
      return newSet;
    });
  };

  const handleEventClick = (event: FutureEvent) => {
    if (onEventClick) {
      onEventClick(event);
    }
  };

  if (loading) {
    return (
      <div className="timeline-container">
        <div className="timeline-loading">加载中...</div>
      </div>
    );
  }

  if (error && timelineDays.length === 0) {
    return (
      <div className="timeline-container">
        <div className="timeline-error">{error}</div>
      </div>
    );
  }

  return (
    <div className="timeline-container">
      <div className="timeline-header">
        <h3>未来时间线</h3>
        <button className="timeline-refresh" onClick={loadTimeline}>
          刷新
        </button>
      </div>

      <div className="timeline-content">
        {timelineDays.map((day) => (
          <div key={day.date} className="timeline-day">
            <div
              className={`timeline-day-header ${expandedDates.has(day.date) ? 'expanded' : ''}`}
              onClick={() => toggleExpand(day.date)}
            >
              <span className="timeline-day-date">{day.displayDate}</span>
              <span className="timeline-day-count">{day.eventCount}</span>
              <span className="timeline-day-expand">
                {expandedDates.has(day.date) ? '▼' : '▶'}
              </span>
            </div>

            {expandedDates.has(day.date) && (
              <div className="timeline-day-events">
                {day.events.map((event) => (
                  <div
                    key={event.id}
                    className="timeline-event"
                    onClick={() => handleEventClick(event)}
                  >
                    <div className="timeline-event-title">
                      {event.title}
                      <span
                        className="timeline-event-status"
                        style={{ backgroundColor: getStatusColor(event.status) }}
                      >
                        {getStatusLabel(event.status)}
                      </span>
                    </div>
                    {event.description && (
                      <div className="timeline-event-description">{event.description}</div>
                    )}
                    <div className="timeline-event-meta">
                      <span className="timeline-event-original">{event.original_expression}</span>
                      <span className="timeline-event-confidence">
                        置信度: {Math.round(event.confidence * 100)}%
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

export default FutureTimeline;
