"""Event retriever for storing and retrieving future timeline events."""

import logging
import uuid
from typing import List, Optional
from datetime import datetime, timedelta

from app.models.database import SessionLocal, FutureEventTable
from app.services.temporal.models import (
    FutureEvent,
    EventStatus,
    GetEventsRequest,
    GetEventsByDateRequest,
    UpdateEventStatusRequest,
)
from app.services.temporal.normalizer import TimeNormalizer


logger = logging.getLogger(__name__)


class EventRetriever:
    """
    Retrieves and manages future timeline events.

    Handles CRUD operations for future events in the database.
    """

    def __init__(self):
        """Initialize event retriever."""
        self.normalizer = TimeNormalizer()

    @staticmethod
    def _parse_enum(value: str, enum_class):
        """Parse string value to enum, handling both old and new formats."""
        if value is None:
            return None
        # If already an enum value, return it
        if isinstance(value, enum_class):
            return value
        # Try direct parsing (for values like "pending")
        try:
            return enum_class(value)
        except ValueError:
            pass
        # Try parsing old format (for values like "EventStatus.PENDING")
        if "." in value:
            short_name = value.split(".")[-1]
            try:
                return enum_class[short_name]
            except (KeyError, ValueError):
                pass
        return value

    def save_events(self, events: List[FutureEvent]) -> List[FutureEvent]:
        """
        Save multiple events to database.

        Args:
            events: List of FutureEvent objects to save

        Returns:
            List of saved FutureEvent objects with IDs
        """
        db = SessionLocal()
        saved_events = []

        try:
            for event in events:
                # Check for similar existing events to avoid duplicates
                existing = db.query(FutureEventTable).filter(
                    FutureEventTable.character_id == event.character_id,
                    FutureEventTable.user_id == event.user_id,
                    FutureEventTable.event_date == event.event_date,
                    FutureEventTable.title == event.title,
                    FutureEventTable.status == "pending"
                ).first()

                if existing:
                    logger.info(f"Similar event already exists, updating: {event.title}")
                    existing.updated_at = datetime.now()
                    if event.description and not existing.description:
                        existing.description = event.description
                    saved_event = FutureEvent(
                        id=str(existing.id),
                        character_id=existing.character_id,
                        user_id=existing.user_id,
                        title=existing.title,
                        description=existing.description,
                        event_date=existing.event_date,
                        source_conversation=existing.source_conversation,
                        tags=existing.tags or [],
                        status=self._parse_enum(existing.status, EventStatus),
                        created_at=existing.created_at,
                        updated_at=existing.updated_at
                    )
                else:
                    # Create new event
                    event_id = str(uuid.uuid4())
                    now = datetime.now()

                    db_event = FutureEventTable(
                        id=event_id,
                        character_id=event.character_id,
                        user_id=event.user_id,
                        title=event.title,
                        description=event.description,
                        event_date=event.event_date,
                        source_conversation=event.source_conversation,
                        tags=event.tags,
                        status=event.status.value,
                        created_at=now,
                        updated_at=None
                    )

                    db.add(db_event)
                    saved_event = FutureEvent(
                        id=event_id,
                        character_id=event.character_id,
                        user_id=event.user_id,
                        title=event.title,
                        description=event.description,
                        event_date=event.event_date,
                        source_conversation=event.source_conversation,
                        tags=event.tags,
                        status=event.status,
                        created_at=now
                    )

                saved_events.append(saved_event)

            db.commit()
            logger.info(f"Saved {len(saved_events)} events to database")
            return saved_events

        except Exception as e:
            db.rollback()
            logger.error(f"Error saving events: {e}")
            raise
        finally:
            db.close()

    def get_future_events(self, request: GetEventsRequest) -> List[FutureEvent]:
        """
        Get future events for a user and character.

        Args:
            request: GetEventsRequest with filters

        Returns:
            List of FutureEvent objects
        """
        db = SessionLocal()

        try:
            # Calculate date range
            today = datetime.now().strftime('%Y-%m-%d')
            end_date = (datetime.now() + timedelta(days=request.days_ahead)).strftime('%Y-%m-%d')

            # Build query
            query = db.query(FutureEventTable).filter(
                FutureEventTable.character_id == request.character_id,
                FutureEventTable.user_id == request.user_id,
                FutureEventTable.event_date >= today,
                FutureEventTable.event_date <= end_date
            )

            # Apply status filter if specified
            if request.status:
                query = query.filter(FutureEventTable.status == str(request.status))

            # Order by date
            query = query.order_by(FutureEventTable.event_date.asc())

            # Execute query
            db_events = query.all()

            # Convert to FutureEvent objects
            events = []
            for db_event in db_events:
                events.append(FutureEvent(
                    id=str(db_event.id),
                    character_id=db_event.character_id,
                    user_id=db_event.user_id,
                    title=db_event.title,
                    description=db_event.description,
                    event_date=db_event.event_date,
                    source_conversation=db_event.source_conversation,
                    tags=db_event.tags or [],
                    status=self._parse_enum(db_event.status, EventStatus),
                    created_at=db_event.created_at,
                    updated_at=db_event.updated_at
                ))

            logger.info(f"Retrieved {len(events)} events for {request.user_id}/{request.character_id}")
            return events

        except Exception as e:
            logger.error(f"Error getting future events: {e}")
            return []
        finally:
            db.close()

    def get_events_by_date(self, request: GetEventsByDateRequest) -> List[FutureEvent]:
        """
        Get events for a specific date.

        Args:
            request: GetEventsByDateRequest

        Returns:
            List of FutureEvent objects for the specified date
        """
        db = SessionLocal()

        try:
            db_events = db.query(FutureEventTable).filter(
                FutureEventTable.character_id == request.character_id,
                FutureEventTable.user_id == request.user_id,
                FutureEventTable.event_date == request.date,
                FutureEventTable.status != "cancelled"
            ).order_by(FutureEventTable.created_at.desc()).all()

            events = []
            for db_event in db_events:
                events.append(FutureEvent(
                    id=str(db_event.id),
                    character_id=db_event.character_id,
                    user_id=db_event.user_id,
                    title=db_event.title,
                    description=db_event.description,
                    event_date=db_event.event_date,
                    source_conversation=db_event.source_conversation,
                    tags=db_event.tags or [],
                    status=self._parse_enum(db_event.status, EventStatus),
                    created_at=db_event.created_at,
                    updated_at=db_event.updated_at
                ))

            return events

        except Exception as e:
            logger.error(f"Error getting events by date: {e}")
            return []
        finally:
            db.close()

    def update_event_status(self, event_id: str, request: UpdateEventStatusRequest) -> Optional[FutureEvent]:
        """
        Update the status of an event.

        Args:
            event_id: ID of the event to update
            request: UpdateEventStatusRequest with new status

        Returns:
            Updated FutureEvent or None if not found
        """
        db = SessionLocal()

        try:
            db_event = db.query(FutureEventTable).filter(
                FutureEventTable.id == event_id
            ).first()

            if not db_event:
                logger.warning(f"Event not found: {event_id}")
                return None

            db_event.status = request.status.value
            db_event.updated_at = datetime.now()

            db.commit()

            logger.info(f"Updated event {event_id} status to {request.status}")

            return FutureEvent(
                id=str(db_event.id),
                character_id=db_event.character_id,
                user_id=db_event.user_id,
                title=db_event.title,
                description=db_event.description,
                event_date=db_event.event_date,
                source_conversation=db_event.source_conversation,
                tags=db_event.tags or [],
                status=request.status,
                created_at=db_event.created_at,
                updated_at=db_event.updated_at
            )

        except Exception as e:
            db.rollback()
            logger.error(f"Error updating event status: {e}")
            return None
        finally:
            db.close()

    def delete_event(self, event_id: str) -> bool:
        """
        Delete an event.

        Args:
            event_id: ID of the event to delete

        Returns:
            True if deleted, False if not found
        """
        db = SessionLocal()

        try:
            db_event = db.query(FutureEventTable).filter(
                FutureEventTable.id == event_id
            ).first()

            if not db_event:
                logger.warning(f"Event not found for deletion: {event_id}")
                return False

            db.delete(db_event)
            db.commit()

            logger.info(f"Deleted event {event_id}")
            return True

        except Exception as e:
            db.rollback()
            logger.error(f"Error deleting event: {e}")
            return False
        finally:
            db.close()

    def get_events_grouped_by_date(self, request: GetEventsRequest) -> dict:
        """
        Get events grouped by date.

        Args:
            request: GetEventsRequest

        Returns:
            Dict with dates as keys and lists of events as values
        """
        events = self.get_future_events(request)

        grouped = {}
        for event in events:
            if event.event_date not in grouped:
                grouped[event.event_date] = []
            grouped[event.event_date].append(event)

        return grouped
