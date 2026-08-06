import json
import uuid

from app.agent.agent_core import agent_engine
from app.db.database import get_db_session
from app.models.api import (
    APIResponse,
    ChatMessageRequest,
    PinnedChartCreate,
)
from fastapi import APIRouter, Body, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api", tags=["Agent & Dashboard"])


@router.post("/chat/stream")
async def chat_stream(request: ChatMessageRequest = Body(...)):
    """
    Streams natural language agent reasoning, tool call progress, and final prose answer over SSE.
    """
    return StreamingResponse(
        agent_engine.stream_agent_execution(request.message),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/pinned-charts", response_model=APIResponse)
async def get_pinned_charts(session: AsyncSession = Depends(get_db_session)):
    """Retrieves all dashboard pinned charts."""
    sql = text("SELECT id, title, description, chart_type, sql_query, chart_spec, created_at FROM pinned_charts ORDER BY created_at DESC;")
    result = await session.execute(sql)
    rows = result.mappings().all()
    pinned = []
    for r in rows:
        d = dict(r)
        if isinstance(d.get("chart_spec"), str):
            d["chart_spec"] = json.loads(d["chart_spec"])
        pinned.append(d)
    return APIResponse(success=True, data=pinned)


@router.post("/pinned-charts", response_model=APIResponse)
async def pin_chart(chart: PinnedChartCreate = Body(...), session: AsyncSession = Depends(get_db_session)):
    """Pins a chart to the dashboard storing its re-runnable SQL query and specification."""
    chart_id = str(uuid.uuid4())[:8]
    sql = text("""
        INSERT INTO pinned_charts (id, title, description, chart_type, sql_query, chart_spec)
        VALUES (:id, :title, :description, :chart_type, :sql_query, :chart_spec)
        RETURNING id, title, description, chart_type, sql_query, chart_spec, created_at;
    """)
    result = await session.execute(sql, {
        "id": chart_id,
        "title": chart.title,
        "description": chart.description,
        "chart_type": chart.chart_type,
        "sql_query": chart.sql_query,
        "chart_spec": json.dumps(chart.chart_spec)
    })
    await session.commit()
    row = dict(result.mappings().one())
    if isinstance(row.get("chart_spec"), str):
        row["chart_spec"] = json.loads(row["chart_spec"])
    return APIResponse(success=True, data=row)


@router.delete("/pinned-charts/{chart_id}", response_model=APIResponse)
async def unpin_chart(chart_id: str, session: AsyncSession = Depends(get_db_session)):
    """Unpins a chart from the dashboard grid."""
    sql = text("DELETE FROM pinned_charts WHERE id = :id;")
    await session.execute(sql, {"id": chart_id})
    await session.commit()
    return APIResponse(success=True, data={"message": f"Chart {chart_id} unpinned successfully."})
