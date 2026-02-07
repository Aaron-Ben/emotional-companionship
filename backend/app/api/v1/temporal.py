"""Temporal API endpoints for future timeline system."""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends

from app.services.llm import LLM
from app.services.temporal import (
    TimeExtractor,
    EventRetriever,
)
from app.services.temporal.models import (
    ExtractTimelineRequest,
    ExtractTimelineResponse,
    GetEventsRequest,
    GetEventsByDateRequest,
    UpdateEventStatusRequest,
    EventStatus,
)
from app.services.temporal.normalizer import TimeNormalizer


# Create router
router = APIRouter(prefix="/api/v1/timeline", tags=["timeline"])

# Configure logging
logger = logging.getLogger(__name__)


def get_llm_service() -> LLM:
    """
    Dependency injection for LLM service.
    Uses OpenRouter by default.
    """
    import os

    # Get model from environment or use default
    model = os.getenv("OPENROUTER_MODEL", "anthropic/claude-3.5-sonnet")

    return LLM(config={"model": model})


def get_mock_user_id() -> str:
    """
    Mock user ID for development.
    In production, this would come from authentication.
    """
    return "user_default"


@router.post("/extract", response_model=ExtractTimelineResponse)
async def extract_timeline(
    request: ExtractTimelineRequest,
    llm: LLM = Depends(get_llm_service)
):
    """
    Extract future timeline events from conversation.

    Request Body:
    - character_id: Character ID
    - user_id: User ID
    - conversation_messages: List of conversation messages

    Returns:
        Extracted events information

    Example:
    ```json
    {
        "character_id": "sister_001",
        "user_id": "user_default",
        "conversation_messages": [
            {"role": "user", "content": "明天下午3点开会，下周去北京旅游"}
        ]
    }
    ```
    """
    try:
        # Extract events using LLM
        extractor = TimeExtractor(llm)
        events = extractor.extract_from_conversation(request)

        # Save events to database
        retriever = EventRetriever()
        saved_events = retriever.save_events(events)

        return ExtractTimelineResponse(
            events_extracted=len(saved_events),
            events=saved_events
        )

    except Exception as e:
        logger.error(f"Error extracting timeline: {e}")
        raise HTTPException(status_code=500, detail=f"Error extracting timeline: {str(e)}")


@router.get("/events")
async def get_future_events(
    character_id: str,
    user_id: str = Depends(get_mock_user_id),
    days_ahead: int = 30,
    status: Optional[EventStatus] = None
):
    """
    Get future events for a user and character.

    Query Parameters:
    - character_id: Character ID
    - user_id: User ID (from auth)
    - days_ahead: Number of days ahead to look (default: 30)
    - status: Filter by status (optional)

    Returns:
        List of future events grouped by date

    Example:
    ```json
    {
        "2026-01-26": [
            {
                "id": "event-123",
                "title": "开会",
                "event_date": "2026-01-26",
                "original_expression": "明天下午3点"
            }
        ]
    }
    ```
    """
    try:
        retriever = EventRetriever()
        request = GetEventsRequest(
            character_id=character_id,
            user_id=user_id,
            days_ahead=days_ahead,
            status=status
        )

        events = retriever.get_future_events(request)

        # Group by date
        grouped = {}
        for event in events:
            if event.event_date not in grouped:
                grouped[event.event_date] = []
            grouped[event.event_date].append(event)

        # Format with display dates
        result = {}
        normalizer = TimeNormalizer()
        for date, events_list in grouped.items():
            display_date = normalizer.format_display_date(date)
            result[display_date] = [
                {
                    "id": e.id,
                    "title": e.title,
                    "description": e.description,
                    "event_date": e.event_date,
                    "status": e.status,
                    "tags": e.tags,
                    "source_conversation": e.source_conversation,
                    "created_at": e.created_at.isoformat() if e.created_at else None,
                    "updated_at": e.updated_at.isoformat() if e.updated_at else None,
                }
                for e in events_list
            ]

        return result

    except Exception as e:
        logger.error(f"Error getting future events: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting future events: {str(e)}")


@router.post("/events/by-date")
async def get_events_by_date(
    request: GetEventsByDateRequest
):
    """
    Get events for a specific date.

    Request Body:
    - character_id: Character ID
    - user_id: User ID
    - date: Date in YYYY-MM-DD format

    Returns:
        List of events for the specified date
    """
    try:
        retriever = EventRetriever()
        events = retriever.get_events_by_date(request)

        return [
            {
                "id": e.id,
                "title": e.title,
                "description": e.description,
                "event_date": e.event_date,
                "status": e.status,
                "tags": e.tags,
                "source_conversation": e.source_conversation,
                "created_at": e.created_at.isoformat() if e.created_at else None,
                "updated_at": e.updated_at.isoformat() if e.updated_at else None,
            }
            for e in events
        ]

    except Exception as e:
        logger.error(f"Error getting events by date: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting events by date: {str(e)}")


@router.put("/events/{event_id}/status")
async def update_event_status(
    event_id: str,
    request: UpdateEventStatusRequest
):
    """
    Update the status of an event.

    Path Parameters:
    - event_id: ID of the event to update

    Request Body:
    - status: New status (pending/completed/cancelled)

    Returns:
        Updated event
    """
    try:
        retriever = EventRetriever()
        updated_event = retriever.update_event_status(event_id, request)

        if not updated_event:
            raise HTTPException(status_code=404, detail=f"Event not found: {event_id}")

        return {
            "id": updated_event.id,
            "title": updated_event.title,
            "status": updated_event.status,
            "updated_at": updated_event.updated_at.isoformat() if updated_event.updated_at else None,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating event status: {e}")
        raise HTTPException(status_code=500, detail=f"Error updating event status: {str(e)}")


@router.delete("/events/{event_id}")
async def delete_event(event_id: str):
    """
    Delete an event.

    Path Parameters:
    - event_id: ID of the event to delete

    Returns:
        Success message
    """
    try:
        retriever = EventRetriever()
        success = retriever.delete_event(event_id)

        if not success:
            raise HTTPException(status_code=404, detail=f"Event not found: {event_id}")

        return {"message": "Event deleted successfully", "id": event_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting event: {e}")
        raise HTTPException(status_code=500, detail=f"Error deleting event: {str(e)}")
