/** Event Detail Modal - Shows full event details with status management */

import React, { useState } from 'react';
import type { FutureEvent } from '../../types/timeline';
import {
  updateEventStatus,
  getStatusLabel,
  getStatusColor,
  formatDisplayDate,
} from '../../services/timelineService';

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

  if (!isOpen) {
    return null;
  }

  return (
    <div
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-[1100] animate-in fade-in duration-200"
      onClick={onClose}
    >
      <div
        className="w-[90%] max-w-[450px] max-h-[85vh] bg-white rounded-2xl shadow-2xl flex flex-col animate-in slide-in-from-bottom-4 duration-300"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-5 bg-gradient-to-r from-sky-400 to-blue-500 rounded-t-2xl">
          <h3 className="text-lg font-semibold text-white">{event.title}</h3>
          <button
            className="w-8 h-8 rounded-full bg-white/20 text-white flex items-center justify-center hover:bg-white/30 transition-all hover:rotate-90 duration-200"
            onClick={onClose}
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Body */}
        <div
          className="flex-1 overflow-y-auto px-6 py-5"
          style={{
            scrollbarWidth: 'thin',
            scrollbarColor: '#ccc #f0f0f0',
          }}
        >
          {error && (
            <div className="flex items-center justify-between p-3 mb-4 bg-red-50 border border-red-200 rounded-lg text-red-500 text-sm">
              <span>{error}</span>
              <button
                onClick={() => setError(null)}
                className="w-5 h-5 flex items-center justify-center text-red-500 hover:bg-red-100 rounded"
              >
                ×
              </button>
            </div>
          )}

          {/* 状态 */}
          <div className="mb-5">
            <label className="block mb-2 text-xs font-medium text-gray-500 uppercase tracking-wider">
              状态
            </label>
            <div className="flex items-center">
              <span
                className="px-3.5 py-1.5 text-sm font-medium text-white rounded-full"
                style={{ backgroundColor: getStatusColor(event.status) }}
              >
                {getStatusLabel(event.status)}
              </span>
            </div>
          </div>

          {/* 描述 */}
          {event.description && (
            <div className="mb-5">
              <label className="block mb-2 text-xs font-medium text-gray-500 uppercase tracking-wider">
                描述
              </label>
              <p className="text-sm text-gray-800 leading-relaxed">{event.description}</p>
            </div>
          )}

          {/* 日期 */}
          <div className="mb-5">
            <label className="block mb-2 text-xs font-medium text-gray-500 uppercase tracking-wider">
              日期
            </label>
            <p className="text-sm text-gray-800">{formatDisplayDate(event.event_date)}</p>
          </div>

          {/* 来源对话 */}
          {event.source_conversation && (
            <div className="mb-5">
              <label className="block mb-2 text-xs font-medium text-gray-500 uppercase tracking-wider">
                来源对话
              </label>
              <p className="text-sm text-gray-600 bg-gray-50 px-3.5 py-2.5 rounded-lg border-l-3 border-sky-400 leading-relaxed">
                {event.source_conversation}
              </p>
            </div>
          )}

          {/* 标签 */}
          {event.tags && event.tags.length > 0 && (
            <div className="mb-5">
              <label className="block mb-2 text-xs font-medium text-gray-500 uppercase tracking-wider">
                标签
              </label>
              <div className="flex flex-wrap gap-2">
                {event.tags.map((tag, index) => (
                  <span
                    key={index}
                    className="px-2.5 py-1 text-xs bg-sky-50 text-sky-500 rounded-full border border-sky-200"
                  >
                    {tag}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* 创建时间 */}
          <div className="mb-5">
            <label className="block mb-2 text-xs font-medium text-gray-500 uppercase tracking-wider">
              创建时间
            </label>
            <p className="text-sm text-gray-800">
              {event.created_at
                ? new Date(event.created_at).toLocaleString('zh-CN')
                : '未知'}
            </p>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-gray-200 flex gap-3 flex-wrap bg-gray-50 rounded-b-2xl">
          {event.status === 'pending' && (
            <>
              <button
                className="flex-1 min-w-[100px] px-4 py-2.5 bg-green-500 text-white text-sm font-medium rounded-lg hover:bg-green-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                onClick={() => handleStatusChange('completed')}
                disabled={loading}
              >
                标记为完成
              </button>
              <button
                className="flex-1 min-w-[100px] px-4 py-2.5 bg-red-500 text-white text-sm font-medium rounded-lg hover:bg-red-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                onClick={() => handleStatusChange('cancelled')}
                disabled={loading}
              >
                标记为取消
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default EventDetailModal;
