-- Enable required PostgreSQL extensions for enhanced monitoring
-- pg_stat_statements: Track query performance statistics
-- pg_anon: Data anonymization for development/testing

-- Enable pg_stat_statements for query statistics
-- This provides query execution statistics for performance monitoring
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Enable pg_anon for data anonymization
-- This provides functions for anonymizing sensitive data in dev/test environments
CREATE EXTENSION IF NOT EXISTS anon;

-- Create view for frequently executed queries
CREATE OR REPLACE VIEW slow_queries AS
SELECT 
    query,
    calls,
    total_exec_time,
    mean_exec_time,
    stddev_exec_time,
    max_exec_time,
    min_exec_time
FROM pg_stat_statements 
WHERE mean_exec_time > 100  -- Queries taking more than 100ms on average
ORDER BY mean_exec_time DESC
LIMIT 20;

-- Create view for database statistics summary
CREATE OR REPLACE VIEW database_stats_summary AS
SELECT 
    'total_queries' as metric_name,
    SUM(calls) as metric_value,
    'Total number of queries executed' as description
FROM pg_stat_statements
UNION ALL
SELECT 
    'avg_execution_time' as metric_name,
    AVG(mean_exec_time) as metric_value,
    'Average query execution time in milliseconds' as description
FROM pg_stat_statements
UNION ALL
SELECT 
    'total_execution_time' as metric_name,
    SUM(total_exec_time) as metric_value,
    'Total time spent executing queries in milliseconds' as description
FROM pg_stat_statements;

-- Create function to get query performance metrics
CREATE OR REPLACE FUNCTION get_query_performance_stats(
    limit_entries INTEGER DEFAULT 10
) RETURNS TABLE(
    query TEXT,
    calls BIGINT,
    total_exec_time DOUBLE PRECISION,
    mean_exec_time DOUBLE PRECISION,
    rows_per_call DOUBLE PRECISION
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        LEFT(query, 100) as query,  -- Truncate very long queries
        calls,
        total_exec_time,
        mean_exec_time,
        CASE 
            WHEN calls > 0 THEN total_exec_time / calls 
            ELSE 0 
        END as rows_per_call
    FROM pg_stat_statements 
    ORDER BY mean_exec_time DESC
    LIMIT limit_entries;
END;
$$ LANGUAGE plpgsql;

-- Create function to anonymize sample data for development
CREATE OR REPLACE FUNCTION anonymize_sensitive_data(
    input_data TEXT,
    anonymization_level INTEGER DEFAULT 1  -- 1: partial, 2: full
) RETURNS TEXT AS $$
BEGIN
    -- Use pg_anon extension functions if available
    IF anonymization_level = 1 THEN
        -- Partial anonymization (mask middle characters)
        RETURN CASE 
            WHEN LENGTH(input_data) <= 4 THEN '****'
            WHEN LENGTH(input_data) <= 8 THEN LEFT(input_data, 2) || '****' || RIGHT(input_data, 2)
            ELSE LEFT(input_data, 4) || '****' || RIGHT(input_data, 4)
        END;
    ELSIF anonymization_level = 2 THEN
        -- Full anonymization
        RETURN 'ANONYMIZED';
    ELSE
        RETURN input_data;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Grant appropriate permissions
GRANT SELECT ON slow_queries TO PUBLIC;
GRANT SELECT ON database_stats_summary TO PUBLIC;
GRANT EXECUTE ON FUNCTION get_query_performance_stats TO PUBLIC;
GRANT EXECUTE ON FUNCTION anonymize_sensitive_data TO PUBLIC;

-- Add comments
COMMENT ON EXTENSION pg_stat_statements IS 'Query execution statistics for performance monitoring';
COMMENT ON EXTENSION anon IS 'Data anonymization utilities for development environments';
COMMENT ON VIEW slow_queries IS 'View of slow executing queries (>100ms avg)';
COMMENT ON VIEW database_stats_summary IS 'Summary view of database performance metrics';
COMMENT ON FUNCTION get_query_performance_stats IS 'Returns query performance statistics';
COMMENT ON FUNCTION anonymize_sensitive_data IS 'Anonymizes sensitive data for dev/test environments';

-- Create index on pg_stat_statements for better performance
CREATE INDEX IF NOT EXISTS idx_pg_stat_statements_mean_time 
ON pg_stat_statements(mean_exec_time DESC);

CREATE INDEX IF NOT EXISTS idx_pg_stat_statements_calls 
ON pg_stat_statements(calls DESC);