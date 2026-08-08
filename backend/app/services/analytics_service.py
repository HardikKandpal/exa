from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class AnalyticsService:

    @staticmethod
    async def get_channel_activity_daily(
        session: AsyncSession,
        server_id: str | None = None,
        limit: int = 30
    ) -> list[dict[str, Any]]:
        """Computes daily message count per channel in DB."""
        query = """
            SELECT
                cds.date,
                c.channel_name,
                s.server_name,
                SUM(cds.message_count) as total_messages,
                AVG(cds.active_users) as avg_active_users
            FROM channel_daily_stats cds
            JOIN channels c ON cds.channel_id = c.channel_id
            JOIN servers s ON cds.server_id = s.server_id
            WHERE (:server_id IS NULL OR cds.server_id = :server_id)
            GROUP BY cds.date, c.channel_name, s.server_name
            ORDER BY cds.date DESC
            LIMIT :limit;
        """
        result = await session.execute(text(query), {"server_id": server_id, "limit": limit})
        rows = result.mappings().all()
        return [dict(r) for r in rows]

    @staticmethod
    async def get_member_growth_over_time(
        session: AsyncSession,
        server_id: str | None = None
    ) -> list[dict[str, Any]]:
        """Computes cumulative and new member growth trends over time in DB."""
        query = """
            SELECT
                ds.date,
                ds.server_id,
                s.server_name,
                ds.new_members,
                ds.total_members,
                ds.active_members
            FROM daily_stats ds
            JOIN servers s ON ds.server_id = s.server_id
            WHERE (:server_id IS NULL OR ds.server_id = :server_id)
            ORDER BY ds.date ASC;
        """
        result = await session.execute(text(query), {"server_id": server_id})
        rows = result.mappings().all()
        return [dict(r) for r in rows]

    @staticmethod
    async def get_hourly_message_distribution(
        session: AsyncSession,
        server_id: str | None = None
    ) -> list[dict[str, Any]]:
        """Computes hourly distribution of messages directly in DB using EXTRACT(HOUR)."""
        query = """
            SELECT
                EXTRACT(HOUR FROM m.timestamp) as hour_of_day,
                COUNT(m.message_id) as message_count,
                COUNT(DISTINCT m.user_id) as unique_posters
            FROM messages m
            WHERE (:server_id IS NULL OR m.server_id = :server_id)
            GROUP BY hour_of_day
            ORDER BY hour_of_day ASC;
        """
        result = await session.execute(text(query), {"server_id": server_id})
        rows = result.mappings().all()
        return [dict(r) for r in rows]
