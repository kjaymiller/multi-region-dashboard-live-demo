"""PostgreSQL query definitions for the Multi-Region Dashboard."""

# Connection information query - returns server details
CONNECTION_INFO = """
SELECT
    inet_server_addr()::text AS server_ip,
    pg_backend_pid() AS backend_pid,
    version() AS pg_version
"""

# Cache hit ratio query - measures buffer cache effectiveness
CACHE_HIT_RATIO = """
SELECT
    ROUND(
        CASE
            WHEN blks_hit + blks_read = 0 THEN 0
            ELSE (blks_hit::float / (blks_hit + blks_read) * 100)
        END, 2
    ) AS cache_hit_ratio,
    blks_hit,
    blks_read
FROM pg_stat_database
WHERE datname = current_database()
"""

# Active connections query
ACTIVE_CONNECTIONS = """
SELECT
    count(*) FILTER (WHERE state = 'active') AS active_connections,
    count(*) FILTER (WHERE state = 'idle') AS idle_connections,
    count(*) FILTER (WHERE state = 'idle in transaction') AS idle_in_transaction,
    count(*) AS total_connections
FROM pg_stat_activity
WHERE datname = current_database()
"""

# Database size query
DATABASE_SIZE = """
SELECT
    pg_size_pretty(pg_database_size(current_database())) AS db_size,
    pg_database_size(current_database()) AS db_size_bytes
"""

# Database statistics query
DATABASE_STATS = """
SELECT
    numbackends AS current_connections,
    xact_commit AS transactions_committed,
    xact_rollback AS transactions_rolled_back,
    tup_returned AS rows_returned,
    tup_fetched AS rows_fetched,
    tup_inserted AS rows_inserted,
    tup_updated AS rows_updated,
    tup_deleted AS rows_deleted
FROM pg_stat_database
WHERE datname = current_database()
"""

# Slow queries from pg_stat_statements (requires extension)
SLOW_QUERIES = """
SELECT
    query,
    calls,
    ROUND(total_exec_time::numeric / 1000, 2) AS total_time_seconds,
    ROUND(mean_exec_time::numeric, 2) AS mean_time_ms,
    ROUND(max_exec_time::numeric, 2) AS max_time_ms,
    rows
FROM pg_stat_statements
WHERE userid = (SELECT usesysid FROM pg_user WHERE usename = current_user)
ORDER BY total_exec_time DESC
LIMIT 10
"""

# Check if pg_stat_statements is available
CHECK_PG_STAT_STATEMENTS = """
SELECT EXISTS (
    SELECT 1 FROM pg_extension WHERE extname = 'pg_stat_statements'
) AS available
"""

# Replication status (for read replicas)
REPLICATION_STATUS = """
SELECT
    pg_is_in_recovery() AS is_replica,
    CASE
        WHEN pg_is_in_recovery() THEN pg_last_wal_receive_lsn()::text
        ELSE pg_current_wal_lsn()::text
    END AS current_lsn,
    CASE
        WHEN pg_is_in_recovery() THEN
            EXTRACT(EPOCH FROM (now() - pg_last_xact_replay_timestamp()))::integer
        ELSE 0
    END AS replication_lag_seconds
"""
