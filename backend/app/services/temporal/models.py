"""Temporal data models for future timeline system."""

from enum import Enum
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class EventStatus(str, Enum):
    """Status of a future event."""
    PENDING = "pending"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class FutureEvent(BaseModel):
    """A future event extracted from conversation."""
    id: Optional[str] = None
    character_id: str = Field(..., description="角色ID")
    user_id: str = Field(..., description="用户ID")
    title: str = Field(..., description="事件标题")
    description: Optional[str] = Field(None, description="事件详细描述")
    event_date: str = Field(..., description="事件日期 YYYY-MM-DD")
    source_conversation: Optional[str] = Field(None, description="来源对话内容")
    tags: List[str] = Field(default_factory=list, description="事件标签")
    status: EventStatus = Field(default=EventStatus.PENDING, description="事件状态")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class TimelineDay(BaseModel):
    """Represents a day in the timeline with events."""
    date: str = Field(..., description="日期 YYYY-MM-DD")
    display_date: str = Field(..., description="显示日期 如 '1月26日 周一'")
    events: List[FutureEvent] = Field(default_factory=list, description="当天的事件列表")
    event_count: int = Field(default=0, description="事件数量")


class TimelineWeek(BaseModel):
    """Represents a week in the timeline."""
    week_number: int = Field(..., description="周数")
    start_date: str = Field(..., description="开始日期")
    end_date: str = Field(..., description="结束日期")
    days: List[TimelineDay] = Field(default_factory=list, description="周内的日期")


class ExtractTimelineRequest(BaseModel):
    """Request for timeline extraction from conversation."""
    character_id: str = Field(..., description="角色ID")
    user_id: str = Field(..., description="用户ID")
    conversation_messages: List[dict] = Field(..., description="对话消息列表")


class ExtractTimelineResponse(BaseModel):
    """Response from timeline extraction."""
    events_extracted: int = Field(..., description="提取的事件数量")
    events: List[FutureEvent] = Field(default_factory=list, description="提取的事件列表")


class GetEventsRequest(BaseModel):
    """Request for getting future events."""
    character_id: str = Field(..., description="角色ID")
    user_id: str = Field(..., description="用户ID")
    days_ahead: int = Field(default=30, description="获取未来N天的事件")
    status: Optional[EventStatus] = Field(None, description="按状态筛选")


class GetEventsByDateRequest(BaseModel):
    """Request for getting events by specific date."""
    character_id: str = Field(..., description="角色ID")
    user_id: str = Field(..., description="用户ID")
    date: str = Field(..., description="查询日期 YYYY-MM-DD")


class UpdateEventStatusRequest(BaseModel):
    """Request for updating event status."""
    status: EventStatus = Field(..., description="新状态")
