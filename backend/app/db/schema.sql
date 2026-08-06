-- Relational Schema for Discord Analytics Platform

-- 1. Servers Table
CREATE TABLE IF NOT EXISTS servers (
    server_id VARCHAR(64) PRIMARY KEY,
    server_name VARCHAR(255) NOT NULL,
    owner_id VARCHAR(64) NOT NULL,
    creation_date TIMESTAMP WITH TIME ZONE NOT NULL,
    region VARCHAR(32) NOT NULL,
    verification_level INT DEFAULT 0,
    default_message_notifications INT DEFAULT 0,
    explicit_content_filter INT DEFAULT 0,
    system_channel_id VARCHAR(64),
    afk_channel_id VARCHAR(64),
    afk_timeout FLOAT,
    widget_enabled BOOLEAN DEFAULT FALSE,
    premium_tier INT DEFAULT 0,
    premium_subscription_count INT DEFAULT 0,
    approximate_member_count INT DEFAULT 0,
    approximate_presence_count INT DEFAULT 0
);

-- 2. Channels Table
CREATE TABLE IF NOT EXISTS channels (
    channel_id VARCHAR(64) PRIMARY KEY,
    server_id VARCHAR(64) REFERENCES servers(server_id) ON DELETE CASCADE,
    channel_name VARCHAR(255) NOT NULL,
    channel_type VARCHAR(32) NOT NULL,
    topic TEXT,
    nsfw BOOLEAN DEFAULT FALSE,
    rate_limit_per_user INT DEFAULT 0,
    position INT DEFAULT 0
);

-- 3. Members Table
CREATE TABLE IF NOT EXISTS members (
    user_id VARCHAR(64) NOT NULL,
    server_id VARCHAR(64) REFERENCES servers(server_id) ON DELETE CASCADE,
    username VARCHAR(255) NOT NULL,
    display_name VARCHAR(255),
    discriminator VARCHAR(10),
    avatar_hash VARCHAR(255),
    is_bot BOOLEAN DEFAULT FALSE,
    join_date TIMESTAMP WITH TIME ZONE NOT NULL,
    last_active TIMESTAMP WITH TIME ZONE,
    roles TEXT,
    messages_sent INT DEFAULT 0,
    voice_minutes INT DEFAULT 0,
    is_owner BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (server_id, user_id)
);

-- 4. Daily Server Stats Table
CREATE TABLE IF NOT EXISTS daily_stats (
    server_id VARCHAR(64) REFERENCES servers(server_id) ON DELETE CASCADE,
    date DATE NOT NULL,
    total_messages INT DEFAULT 0,
    new_members INT DEFAULT 0,
    active_members INT DEFAULT 0,
    total_members INT DEFAULT 0,
    day_of_week INT NOT NULL,
    is_weekend INT NOT NULL,
    PRIMARY KEY (server_id, date)
);

-- 5. Daily Channel Stats Table
CREATE TABLE IF NOT EXISTS channel_daily_stats (
    channel_id VARCHAR(64) REFERENCES channels(channel_id) ON DELETE CASCADE,
    server_id VARCHAR(64) REFERENCES servers(server_id) ON DELETE CASCADE,
    date DATE NOT NULL,
    message_count INT DEFAULT 0,
    active_users INT DEFAULT 0,
    PRIMARY KEY (channel_id, date)
);

-- 6. Messages Sample Table
CREATE TABLE IF NOT EXISTS messages (
    message_id VARCHAR(64) PRIMARY KEY,
    server_id VARCHAR(64) REFERENCES servers(server_id) ON DELETE CASCADE,
    channel_id VARCHAR(64) REFERENCES channels(channel_id) ON DELETE CASCADE,
    user_id VARCHAR(64) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    content TEXT,
    has_attachment BOOLEAN DEFAULT FALSE,
    has_embed BOOLEAN DEFAULT FALSE,
    reaction_count INT DEFAULT 0,
    is_pinned BOOLEAN DEFAULT FALSE,
    length INT DEFAULT 0
);

-- 7. Pinned Dashboard Charts Table
CREATE TABLE IF NOT EXISTS pinned_charts (
    id VARCHAR(64) PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    chart_type VARCHAR(32) NOT NULL,
    sql_query TEXT NOT NULL,
    chart_spec JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Performance Indexes for Time-Series & Querying
CREATE INDEX IF NOT EXISTS idx_channels_server ON channels(server_id);
CREATE INDEX IF NOT EXISTS idx_members_user ON members(user_id);
CREATE INDEX IF NOT EXISTS idx_daily_stats_date ON daily_stats(date);
CREATE INDEX IF NOT EXISTS idx_daily_stats_server_date ON daily_stats(server_id, date);
CREATE INDEX IF NOT EXISTS idx_channel_daily_stats_date ON channel_daily_stats(date);
CREATE INDEX IF NOT EXISTS idx_channel_daily_stats_chan_date ON channel_daily_stats(channel_id, date);
CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp);
CREATE INDEX IF NOT EXISTS idx_messages_server_chan ON messages(server_id, channel_id);

-- Read-Only Role Creation and Security Privileges
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'discord_readonly') THEN
        CREATE ROLE discord_readonly WITH LOGIN PASSWORD 'readonly_secure_password';
    END IF;
END $$;

GRANT CONNECT ON DATABASE discord_analytics TO discord_readonly;
GRANT USAGE ON SCHEMA public TO discord_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO discord_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO discord_readonly;
