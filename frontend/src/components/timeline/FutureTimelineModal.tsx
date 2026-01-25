/** Future Timeline Modal - Floating button modal for timeline view */

import React, { useState } from 'react';
import { FutureTimeline } from './FutureTimeline';
import type { FutureEvent } from '../../types/timeline';
import { EventDetailModal } from './EventDetailModal';

interface FutureTimelineModalProps {
  characterId: string;
  userId?: string;
  daysAhead?: number;
  isOpen: boolean;
  onClose: () => void;
}

export const FutureTimelineModal: React.FC<FutureTimelineModalProps> = ({
  characterId,
  userId = 'user_default',
  daysAhead = 30,
  isOpen,
  onClose,
}) => {
  const [selectedEvent, setSelectedEvent] = useState<FutureEvent | null>(null);
  const [showEventDetail, setShowEventDetail] = useState(false);

  const handleEventClick = (event: FutureEvent) => {
    setSelectedEvent(event);
    setShowEventDetail(true);
  };

  const handleEventDetailClose = () => {
    setShowEventDetail(false);
    setSelectedEvent(null);
  };

  const handleEventUpdate = () => {
    setShowEventDetail(false);
    setSelectedEvent(null);
  };

  if (!isOpen) {
    return null;
  }

  return (
    <>
      <div
        className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 animate-in fade-in duration-200"
        onClick={onClose}
      >
        <div
          className="w-[90%] max-w-2xl max-h-[80vh] bg-white rounded-2xl shadow-2xl flex flex-col animate-in slide-in-from-bottom-4 duration-300"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-4 bg-gradient-to-r from-sky-400 to-blue-500 rounded-t-2xl">
            <h2 className="text-xl font-semibold text-white">未来时间线</h2>
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
            className="flex-1 overflow-y-auto p-6"
            style={{
              scrollbarWidth: 'thin',
              scrollbarColor: '#ccc #f0f0f0',
            }}
          >
            <FutureTimeline
              characterId={characterId}
              userId={userId}
              daysAhead={daysAhead}
              onEventClick={handleEventClick}
            />
          </div>
        </div>
      </div>

      {showEventDetail && selectedEvent && (
        <EventDetailModal
          event={selectedEvent}
          isOpen={showEventDetail}
          onClose={handleEventDetailClose}
          onUpdate={handleEventUpdate}
        />
      )}
    </>
  );
};

export default FutureTimelineModal;
