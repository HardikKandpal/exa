import asyncio
import logging
import os
import re
import sys
from datetime import date, datetime

import numpy as np
import pandas as pd
from app.db.database import AsyncSessionWrite
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def resolve_dataset_dir() -> str:
    env_dir = os.environ.get("DATASET_DIR")
    if env_dir and os.path.exists(env_dir):
        return env_dir

    candidates = [
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "discord_analytics_dataset")),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "discord_analytics_dataset")),
        os.path.abspath("discord_analytics_dataset"),
        "/app/discord_analytics_dataset",
    ]
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate
    return candidates[0]


DATASET_DIR = resolve_dataset_dir()


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Replace NaN and Inf values with None for SQL compatibility."""
    df = df.replace({np.nan: None, np.inf: None, -np.inf: None})
    return df


def parse_dt(val):
    if pd.isna(val) or val is None or val == "":
        return None
    if isinstance(val, (datetime, date)):
        return val
    try:
        return pd.to_datetime(val).to_pydatetime()
    except Exception:
        return None


def parse_date(val):
    if pd.isna(val) or val is None or val == "":
        return None
    if isinstance(val, date) and not isinstance(val, datetime):
        return val
    try:
        return pd.to_datetime(val).date()
    except Exception:
        return None


async def create_schema_if_not_exists(session: AsyncSession):
    """Executes schema.sql DDL to prepare database tables."""
    schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
    if not os.path.exists(schema_path):
        logger.error(f"schema.sql not found at {schema_path}")
        return

    with open(schema_path, "r", encoding="utf-8") as f:
        sql_text = f.read()

    do_blocks = []

    def replace_do(match):
        do_blocks.append(match.group(0))
        return "\n-- DO_BLOCK_PLACEHOLDER --\n"

    cleaned_text = re.sub(r'DO\s+\$\$.*?\$\$\s*;', replace_do, sql_text, flags=re.DOTALL | re.IGNORECASE)

    raw_statements = [s.strip() for s in cleaned_text.split(";") if s.strip()]

    do_idx = 0
    statements = []
    for stmt in raw_statements:
        if "-- DO_BLOCK_PLACEHOLDER --" in stmt:
            if do_idx < len(do_blocks):
                statements.append(do_blocks[do_idx])
                do_idx += 1
        else:
            statements.append(stmt)

    for stmt in statements:
        lines = [line for line in stmt.splitlines() if not line.strip().startswith("--")]
        cleaned_stmt = "\n".join(lines).strip()
        if not cleaned_stmt:
            continue
        try:
            await session.execute(text(cleaned_stmt))
            await session.commit()
        except Exception as e:
            logger.warning(f"Schema statement execution warning: {e}")
            await session.rollback()

    logger.info("Database schema applied successfully.")


async def ingest_servers(session: AsyncSession, dataset_path: str):
    csv_file = os.path.join(dataset_path, "servers.csv")
    if not os.path.exists(csv_file):
        logger.error(f"CSV file not found: {csv_file}")
        return
    df = clean_dataframe(pd.read_csv(csv_file))

    for _, row in df.iterrows():
        sql = text("""
            INSERT INTO servers (
                server_id, server_name, owner_id, creation_date, region, verification_level,
                default_message_notifications, explicit_content_filter, system_channel_id,
                afk_channel_id, afk_timeout, widget_enabled, premium_tier,
                premium_subscription_count, approximate_member_count, approximate_presence_count
            ) VALUES (
                :server_id, :server_name, :owner_id, :creation_date, :region, :verification_level,
                :default_message_notifications, :explicit_content_filter, :system_channel_id,
                :afk_channel_id, :afk_timeout, :widget_enabled, :premium_tier,
                :premium_subscription_count, :approximate_member_count, :approximate_presence_count
            ) ON CONFLICT (server_id) DO NOTHING;
        """)
        await session.execute(sql, {
            "server_id": str(row['server_id']),
            "server_name": str(row['server_name']),
            "owner_id": str(row['owner_id']),
            "creation_date": parse_dt(row['creation_date']),
            "region": str(row['region']),
            "verification_level": int(row['verification_level']) if row['verification_level'] is not None else 0,
            "default_message_notifications": int(row['default_message_notifications']) if row['default_message_notifications'] is not None else 0,
            "explicit_content_filter": int(row['explicit_content_filter']) if row['explicit_content_filter'] is not None else 0,
            "system_channel_id": str(row['system_channel_id']) if row['system_channel_id'] else None,
            "afk_channel_id": str(row['afk_channel_id']) if row['afk_channel_id'] else None,
            "afk_timeout": float(row['afk_timeout']) if row['afk_timeout'] is not None else None,
            "widget_enabled": bool(row['widget_enabled']) if row['widget_enabled'] is not None else False,
            "premium_tier": int(row['premium_tier']) if row['premium_tier'] is not None else 0,
            "premium_subscription_count": int(row['premium_subscription_count']) if row['premium_subscription_count'] is not None else 0,
            "approximate_member_count": int(row['approximate_member_count']) if row['approximate_member_count'] is not None else 0,
            "approximate_presence_count": int(row['approximate_presence_count']) if row['approximate_presence_count'] is not None else 0,
        })
    await session.commit()
    logger.info(f"Ingested {len(df)} servers.")


async def ingest_channels(session: AsyncSession, dataset_path: str):
    csv_file = os.path.join(dataset_path, "channels.csv")
    if not os.path.exists(csv_file):
        logger.error(f"CSV file not found: {csv_file}")
        return
    df = clean_dataframe(pd.read_csv(csv_file))

    for _, row in df.iterrows():
        sql = text("""
            INSERT INTO channels (
                channel_id, server_id, channel_name, channel_type, topic, nsfw,
                rate_limit_per_user, position
            ) VALUES (
                :channel_id, :server_id, :channel_name, :channel_type, :topic, :nsfw,
                :rate_limit_per_user, :position
            ) ON CONFLICT (channel_id) DO NOTHING;
        """)
        await session.execute(sql, {
            "channel_id": str(row['channel_id']),
            "server_id": str(row['server_id']),
            "channel_name": str(row['channel_name']),
            "channel_type": str(row['channel_type']),
            "topic": str(row['topic']) if row['topic'] else None,
            "nsfw": bool(row['nsfw']) if row['nsfw'] is not None else False,
            "rate_limit_per_user": int(row['rate_limit_per_user']) if row['rate_limit_per_user'] is not None else 0,
            "position": int(row['position']) if row['position'] is not None else 0,
        })
    await session.commit()
    logger.info(f"Ingested {len(df)} channels.")


async def ingest_members(session: AsyncSession, dataset_path: str):
    csv_file = os.path.join(dataset_path, "members.csv")
    if not os.path.exists(csv_file):
        logger.error(f"CSV file not found: {csv_file}")
        return
    df = clean_dataframe(pd.read_csv(csv_file))

    for _, row in df.iterrows():
        sql = text("""
            INSERT INTO members (
                user_id, server_id, username, display_name, discriminator, avatar_hash,
                is_bot, join_date, last_active, roles, messages_sent, voice_minutes, is_owner
            ) VALUES (
                :user_id, :server_id, :username, :display_name, :discriminator, :avatar_hash,
                :is_bot, :join_date, :last_active, :roles, :messages_sent, :voice_minutes, :is_owner
            ) ON CONFLICT (server_id, user_id) DO NOTHING;
        """)
        await session.execute(sql, {
            "user_id": str(row['user_id']),
            "server_id": str(row['server_id']),
            "username": str(row['username']),
            "display_name": str(row['display_name']) if row['display_name'] else None,
            "discriminator": str(row['discriminator']) if row['discriminator'] else None,
            "avatar_hash": str(row['avatar_hash']) if row['avatar_hash'] else None,
            "is_bot": bool(row['is_bot']) if row['is_bot'] is not None else False,
            "join_date": parse_dt(row['join_date']),
            "last_active": parse_dt(row['last_active']),
            "roles": str(row['roles']) if row['roles'] else None,
            "messages_sent": int(row['messages_sent']) if row['messages_sent'] is not None else 0,
            "voice_minutes": int(row['voice_minutes']) if row['voice_minutes'] is not None else 0,
            "is_owner": bool(row['is_owner']) if row['is_owner'] is not None else False,
        })
    await session.commit()
    logger.info(f"Ingested {len(df)} members.")


async def ingest_daily_stats(session: AsyncSession, dataset_path: str):
    csv_file = os.path.join(dataset_path, "daily_stats.csv")
    if not os.path.exists(csv_file):
        logger.error(f"CSV file not found: {csv_file}")
        return
    df = clean_dataframe(pd.read_csv(csv_file))

    for _, row in df.iterrows():
        sql = text("""
            INSERT INTO daily_stats (
                server_id, date, total_messages, new_members, active_members,
                total_members, day_of_week, is_weekend
            ) VALUES (
                :server_id, :date, :total_messages, :new_members, :active_members,
                :total_members, :day_of_week, :is_weekend
            ) ON CONFLICT (server_id, date) DO NOTHING;
        """)
        await session.execute(sql, {
            "server_id": str(row['server_id']),
            "date": parse_date(row['date']),
            "total_messages": int(row['total_messages']) if row['total_messages'] is not None else 0,
            "new_members": int(row['new_members']) if row['new_members'] is not None else 0,
            "active_members": int(row['active_members']) if row['active_members'] is not None else 0,
            "total_members": int(row['total_members']) if row['total_members'] is not None else 0,
            "day_of_week": int(row['day_of_week']) if row['day_of_week'] is not None else 0,
            "is_weekend": int(row['is_weekend']) if row['is_weekend'] is not None else 0,
        })
    await session.commit()
    logger.info(f"Ingested {len(df)} daily stats records.")


async def ingest_channel_daily_stats(session: AsyncSession, dataset_path: str):
    csv_file = os.path.join(dataset_path, "channel_daily_stats.csv")
    if not os.path.exists(csv_file):
        logger.error(f"CSV file not found: {csv_file}")
        return
    df = clean_dataframe(pd.read_csv(csv_file))

    for _, row in df.iterrows():
        sql = text("""
            INSERT INTO channel_daily_stats (
                channel_id, server_id, date, message_count, active_users
            ) VALUES (
                :channel_id, :server_id, :date, :message_count, :active_users
            ) ON CONFLICT (channel_id, date) DO NOTHING;
        """)
        await session.execute(sql, {
            "channel_id": str(row['channel_id']),
            "server_id": str(row['server_id']),
            "date": parse_date(row['date']),
            "message_count": int(row['message_count']) if row['message_count'] is not None else 0,
            "active_users": int(row['active_users']) if row['active_users'] is not None else 0,
        })
    await session.commit()
    logger.info(f"Ingested {len(df)} channel daily stats records.")


async def ingest_messages(session: AsyncSession, dataset_path: str):
    csv_file = os.path.join(dataset_path, "messages_sample.csv")
    if not os.path.exists(csv_file):
        logger.error(f"CSV file not found: {csv_file}")
        return
    df = clean_dataframe(pd.read_csv(csv_file))

    for _, row in df.iterrows():
        sql = text("""
            INSERT INTO messages (
                message_id, server_id, channel_id, user_id, timestamp, content,
                has_attachment, has_embed, reaction_count, is_pinned, length
            ) VALUES (
                :message_id, :server_id, :channel_id, :user_id, :timestamp, :content,
                :has_attachment, :has_embed, :reaction_count, :is_pinned, :length
            ) ON CONFLICT (message_id) DO NOTHING;
        """)
        await session.execute(sql, {
            "message_id": str(row['message_id']),
            "server_id": str(row['server_id']),
            "channel_id": str(row['channel_id']),
            "user_id": str(row['user_id']),
            "timestamp": parse_dt(row['timestamp']),
            "content": str(row['content']) if row['content'] else "",
            "has_attachment": bool(row['has_attachment']) if row['has_attachment'] is not None else False,
            "has_embed": bool(row['has_embed']) if row['has_embed'] is not None else False,
            "reaction_count": int(row['reaction_count']) if row['reaction_count'] is not None else 0,
            "is_pinned": bool(row['is_pinned']) if row['is_pinned'] is not None else False,
            "length": int(row['length']) if row['length'] is not None else 0,
        })
    await session.commit()
    logger.info(f"Ingested {len(df)} messages sample records.")


async def run_ingestion(dataset_path: str = DATASET_DIR):
    """Entrypoint for running full database ingestion."""
    logger.info(f"Starting database migration and ingestion from {dataset_path}...")
    async with AsyncSessionWrite() as session:
        await create_schema_if_not_exists(session)
        await ingest_servers(session, dataset_path)
        await ingest_channels(session, dataset_path)
        await ingest_members(session, dataset_path)
        await ingest_daily_stats(session, dataset_path)
        await ingest_channel_daily_stats(session, dataset_path)
        await ingest_messages(session, dataset_path)
    logger.info("Data ingestion completed successfully.")


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else DATASET_DIR
    asyncio.run(run_ingestion(path))
