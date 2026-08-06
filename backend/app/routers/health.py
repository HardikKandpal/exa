from app.db.database import get_db_session
from app.models.api import APIResponse
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=APIResponse)
async def health_check(session: AsyncSession = Depends(get_db_session)):
    """Health check endpoint testing database connectivity and system status."""
    try:
        result = await session.execute(text("SELECT 1;"))
        row = result.scalar()
        if row == 1:
            return APIResponse(success=True, data={"status": "healthy", "database": "connected"})
    except Exception as e:
        return APIResponse(success=False, error={"code": "DB_DISCONNECTED", "message": str(e)})

    return APIResponse(success=False, error={"code": "UNKNOWN_HEALTH_STATE", "message": "Database check failed."})
