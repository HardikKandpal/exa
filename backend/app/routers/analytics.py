from app.db.database import get_db_session
from app.models.api import APIResponse
from app.services.analytics_service import AnalyticsService
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


@router.get("/channel-activity", response_model=APIResponse)
async def get_channel_activity(
    server_id: str | None = Query(None),
    limit: int = Query(30, ge=1, le=500),
    session: AsyncSession = Depends(get_db_session)
):
    """Computes daily message activity per channel directly in the database."""
    data = await AnalyticsService.get_channel_activity_daily(session, server_id=server_id, limit=limit)
    return APIResponse(success=True, data=data)


@router.get("/member-growth", response_model=APIResponse)
async def get_member_growth(
    server_id: str | None = Query(None),
    session: AsyncSession = Depends(get_db_session)
):
    """Computes server member growth over time directly in the database."""
    data = await AnalyticsService.get_member_growth_over_time(session, server_id=server_id)
    return APIResponse(success=True, data=data)


@router.get("/hourly-distribution", response_model=APIResponse)
async def get_hourly_distribution(
    server_id: str | None = Query(None),
    session: AsyncSession = Depends(get_db_session)
):
    """Computes hourly message distribution directly in the database."""
    data = await AnalyticsService.get_hourly_message_distribution(session, server_id=server_id)
    return APIResponse(success=True, data=data)
