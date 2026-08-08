from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Any | None = None


class APIResponse(BaseModel):
    success: bool = True
    data: Any | None = None
    error: ErrorDetail | None = None


class ChatMessageRequest(BaseModel):
    message: str = Field(..., description="User prompt in natural language")
    conversation_id: str | None = Field(default=None, description="Optional conversation identifier")
    history: list[dict[str, str]] | None = Field(default=None, description="Optional conversation context history")


class PinnedChartCreate(BaseModel):
    title: str
    description: str | None = None
    chart_type: str
    sql_query: str
    chart_spec: dict[str, Any]


class PinnedChartResponse(BaseModel):
    id: str
    title: str
    description: str | None = None
    chart_type: str
    sql_query: str
    chart_spec: dict[str, Any]
    created_at: datetime


class TimeSeriesQueryRequest(BaseModel):
    server_id: str | None = None
    channel_id: str | None = None
    start_date: str | None = None
    end_date: str | None = None
