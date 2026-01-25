/** Event Detail Modal - Shows full event details with status management */

import React, { useState } from 'react';
import type { FutureEvent } from '../../types/timeline';
import {
  updateEventStatus,
  deleteEvent,
  getStatusLabel,
  getStatusColor,
  getExpressionTypeLabel,
  formatDisplayDate,
} from '../../services/timelineService';
import './EventDetailModal.css';

interface EventDetailModalProps {
  event: FutureEvent;
  isOpen: boolean;
  onClose: () => void;
  onUpdate: () => void;
}

export const EventDetailModal: React.FC<EventDetailModalProps> = ({
  event,
  isOpen,
  onClose,
  onUpdate,
}) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleStatusChange = async (newStatus: 'pending' | 'completed' | 'cancelled') => {
    if (!event.id) return;

    setLoading(true);
    setError(null);

    try {
      await updateEventStatus(event.id, { status: newStatus });
      onUpdate();
    } catch (err) {
      setError(err instanceof Error ? err.message : '更新状态失败');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!event.id) return;

    if (!confirm('确定要删除这个事件吗？')) {
      return;
    }

    setLoading(true);
    setError(null);

    try {
      await deleteEvent(event.id);
      onUpdate();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : '删除事件失败');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) {
    return null;
  }

  return (
    <div className="event-detail-modal-overlay" onClick={onClose}>
      <div
        className="event-detail-modal-content"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="event-detail-modal-header">
          <h3>{event.title}</h3>
          <button className="event-detail-modal-close" onClick={onClose}>
            ×
          </button>
        </div>

        <div className="event-detail-modal-body">
          {error && (
            <div className="event-detail-error">
              {error}
              <button onClick={() => setError(null)} className="error-close">
                ×
              </button>
            </div>
          )}

          <div className="event-detail-section">
            <label>状态</label>
            <div className="event-detail-status">
              <span
                className="status-badge"
                style={{ backgroundColor: getStatusColor(event.status) }}
              >
                {getStatusLabel(event.status)}
              </span>
            </div>
          </div>

          {event.description && (
            <div className="event-detail-section">
              <label>描述</label>
              <p>{event.description}</p>
            </div>
          )}

          <div className="event-detail-section">
            <label>日期</label>
            <p>{formatDisplayDate(event.event_date)}</p>
          </div>

          <div className="event-detail-section">
            <label>原始表达</label>
            <p className="event-detail-original">"{event.original_expression}"</p>
          </div>

          <div className="event-detail-section">
            <label>类型</label>
            <p>{getExpressionTypeLabel(event.expression_type)}</p>
          </div>

          <div className="event-detail-section">
            <label>置信度</label>
            <div className="event-detail-confidence-bar">
              <div
                className="confidence-fill"
                style={{ width: `${event.confidence * 100}%` }}
              />
            </div>
            <span className="confidence-value">{Math.round(event.confidence * 100)}%</span>
          </div>

          {event.source_conversation && (
            <div className="event-detail-section">
              <label>来源对话</label>
              <p className="event-detail-source">{event.source_conversation}</p>
            </div>
          )}

          {event.tags && event.tags.length > 0 && (
            <div className="event-detail-section">
              <label>标签</label>
              <div className="event-detail-tags">
                {event.tags.map((tag, index) => (
                  <span key={index} className="tag">
                    {tag}
                  </span>
                ))}
              </div>
            </div>
          )}

          <div className="event-detail-section">
            <label>创建时间</label>
            <p>
              {event.created_at
                ? new Date(event.created_at).toLocaleString('zh-CN')
                : '未知'}
            </p>
          </div>
        </div>

        <div className="event-detail-modal-footer">
          {event.status === 'pending' && (
            <>
              <button
                className="btn btn-complete"
                onClick={() => handleStatusChange('completed')}
                disabled={loading}
              >
                标记为完成
              </button>
              <button
                className="btn btn-cancel"
                onClick={() => handleStatusChange('cancelled')}
                disabled={loading}
              >
                标记为取消
              </button>
            </>
          )}
          <button
            className="btn btn-delete"
            onClick={handleDelete}
            disabled={loading}
          >
            删除事件
          </button>
        </div>
      </div>
    </div>
  );
};

export default EventDetailModal;
