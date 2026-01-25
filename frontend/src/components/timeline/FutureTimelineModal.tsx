/** Future Timeline Modal - Floating button modal for timeline view */

import React, { useState } from 'react';
import { FutureTimeline } from './FutureTimeline';
import type { FutureEvent } from '../../types/timeline';
import { EventDetailModal } from './EventDetailModal';
import './FutureTimelineModal.css';

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
    // Refresh timeline after event update
    setShowEventDetail(false);
    setSelectedEvent(null);
  };

  if (!isOpen) {
    return null;
  }

  return (
    <>
      <div className="timeline-modal-overlay" onClick={onClose}>
        <div
          className="timeline-modal-content"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="timeline-modal-header">
            <h2>未来时间线</h2>
            <button className="timeline-modal-close" onClick={onClose}>
              ×
            </button>
          </div>

          <div className="timeline-modal-body">
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
