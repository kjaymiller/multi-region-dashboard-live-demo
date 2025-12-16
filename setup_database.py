"""Database setup script - creates tables and populates initial data."""

import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()


async def setup_database():
    """Create database tables and populate with initial data."""
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        print("❌ DATABASE_URL not found in environment variables")
        print("Please set DATABASE_URL in your .env file")
        return False

    try:
        conn = await asyncpg.connect(database_url)
        print(f"✓ Connected to database")

        # Create database_connections table with SERIAL primary key
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS database_connections (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                host VARCHAR(255) NOT NULL,
                port INTEGER NOT NULL CHECK (port >= 1 AND port <= 65535),
                database_name VARCHAR(63) NOT NULL,
                username VARCHAR(63) NOT NULL,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                ssl_mode VARCHAR(20) DEFAULT 'require' CHECK (ssl_mode IN ('require', 'prefer', 'disable')),
                region VARCHAR(50),
                cloud_provider VARCHAR(50),
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes for database_connections
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_database_connections_region 
            ON database_connections(region)
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_database_connections_cloud_provider 
            ON database_connections(cloud_provider)
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_database_connections_is_active 
            ON database_connections(is_active)
        """)
        
        # Create trigger to update updated_at column
        await conn.execute("""
            CREATE OR REPLACE FUNCTION update_updated_at_column()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = CURRENT_TIMESTAMP;
                RETURN NEW;
            END;
            $$ language 'plpgsql'
        """)

        # Drop trigger if exists, then create it
        await conn.execute("""
            DROP TRIGGER IF EXISTS update_database_connections_updated_at ON database_connections
        """)

        await conn.execute("""
            CREATE TRIGGER update_database_connections_updated_at
                BEFORE UPDATE ON database_connections
                FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()
        """)
        
        print("✓ database_connections table created with SERIAL primary key")

        # Create locations table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS locations (
                id SERIAL PRIMARY KEY,
                region_code VARCHAR(50) NOT NULL UNIQUE,
                region_name VARCHAR(100),
                cloud_provider VARCHAR(50),
                latitude NUMERIC(10, 7) NOT NULL,
                longitude NUMERIC(10, 7) NOT NULL,
                country VARCHAR(100),
                city VARCHAR(100),
                description TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("✓ locations table created")

        # Create indexes for locations table
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_locations_region_code ON locations(region_code)
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_locations_cloud_provider ON locations(cloud_provider)
        """)
        print("✓ locations indexes created")

        # Create connection_tests table for TimescaleDB hypertable
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS connection_tests (
                id BIGSERIAL,
                connection_id INTEGER NOT NULL,
                timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                test_type VARCHAR(50) NOT NULL,
                success BOOLEAN NOT NULL,
                latency_ms NUMERIC(10, 2),
                server_ip TEXT,
                pg_version TEXT,
                backend_pid INTEGER,
                error_message TEXT,
                test_data JSONB,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                CONSTRAINT fk_connection
                    FOREIGN KEY (connection_id)
                    REFERENCES database_connections(id)
                    ON DELETE CASCADE
            )
        """)
        print("✓ connection_tests table created")

        # Add test_data column if it doesn't exist (for existing tables)
        try:
            await conn.execute("""
                ALTER TABLE connection_tests
                ADD COLUMN IF NOT EXISTS test_data JSONB
            """)
            print("✓ test_data column ensured in connection_tests")
        except Exception as e:
            print(f"⚠ Note: Could not add test_data column: {e}")

        # Convert to TimescaleDB hypertable if not already converted
        try:
            await conn.execute("""
                SELECT create_hypertable(
                    'connection_tests',
                    'timestamp',
                    if_not_exists => TRUE,
                    migrate_data => TRUE
                )
            """)
            print("✓ connection_tests converted to TimescaleDB hypertable")
        except Exception as e:
            print(f"⚠ Note: Hypertable conversion skipped (may already exist): {e}")

        # Configure compression policy for connection_tests
        compression_after_days = int(os.getenv("TIMESCALE_COMPRESSION_AFTER_DAYS", "7"))
        try:
            # First, enable compression on the hypertable
            await conn.execute("""
                ALTER TABLE connection_tests SET (
                    timescaledb.compress,
                    timescaledb.compress_segmentby = 'connection_id',
                    timescaledb.compress_orderby = 'timestamp DESC'
                )
            """)
            print(f"✓ Compression enabled on connection_tests hypertable")

            # Add compression policy (compress chunks older than X days)
            await conn.execute(f"""
                SELECT add_compression_policy('connection_tests',
                    INTERVAL '{compression_after_days} days',
                    if_not_exists => TRUE
                )
            """)
            print(f"✓ Compression policy added: compress data older than {compression_after_days} days")
        except Exception as e:
            print(f"⚠ Note: Compression policy setup skipped (may already exist): {e}")

        # Configure retention policy for connection_tests
        retention_days = int(os.getenv("TIMESCALE_RETENTION_DAYS", "90"))
        try:
            # Add retention policy (drop chunks older than X days)
            await conn.execute(f"""
                SELECT add_retention_policy('connection_tests',
                    INTERVAL '{retention_days} days',
                    if_not_exists => TRUE
                )
            """)
            print(f"✓ Retention policy added: drop data older than {retention_days} days")
        except Exception as e:
            print(f"⚠ Note: Retention policy setup skipped (may already exist): {e}")

        # Create indexes for connection_tests
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_connection_tests_connection_id
            ON connection_tests(connection_id, timestamp DESC)
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_connection_tests_timestamp
            ON connection_tests(timestamp DESC)
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_connection_tests_success
            ON connection_tests(success, timestamp DESC)
        """)
        print("✓ connection_tests indexes created")

        # Check if locations table has data
        count = await conn.fetchval("SELECT COUNT(*) FROM locations")

        if count == 0:
            print("Populating locations table with region data...")

            # Insert location data
            locations_data = [
                # DigitalOcean regions
                ('do-nyc1', 'New York 1', 'DigitalOcean', 40.7128, -74.0060, 'USA', 'New York', 'DigitalOcean NYC1 datacenter'),
                ('do-nyc2', 'New York 2', 'DigitalOcean', 40.7128, -74.0060, 'USA', 'New York', 'DigitalOcean NYC2 datacenter'),
                ('do-nyc3', 'New York 3', 'DigitalOcean', 40.7128, -74.0060, 'USA', 'New York', 'DigitalOcean NYC3 datacenter'),
                ('do-sfo1', 'San Francisco 1', 'DigitalOcean', 37.7749, -122.4194, 'USA', 'San Francisco', 'DigitalOcean SFO1 datacenter'),
                ('do-sfo2', 'San Francisco 2', 'DigitalOcean', 37.7749, -122.4194, 'USA', 'San Francisco', 'DigitalOcean SFO2 datacenter'),
                ('do-sfo3', 'San Francisco 3', 'DigitalOcean', 37.7749, -122.4194, 'USA', 'San Francisco', 'DigitalOcean SFO3 datacenter'),
                ('do-ams2', 'Amsterdam 2', 'DigitalOcean', 52.3676, 4.9041, 'Netherlands', 'Amsterdam', 'DigitalOcean AMS2 datacenter'),
                ('do-ams3', 'Amsterdam 3', 'DigitalOcean', 52.3676, 4.9041, 'Netherlands', 'Amsterdam', 'DigitalOcean AMS3 datacenter'),
                ('do-sgp1', 'Singapore 1', 'DigitalOcean', 1.3521, 103.8198, 'Singapore', 'Singapore', 'DigitalOcean SGP1 datacenter'),
                ('do-lon1', 'London 1', 'DigitalOcean', 51.5074, -0.1278, 'UK', 'London', 'DigitalOcean LON1 datacenter'),
                ('do-fra1', 'Frankfurt 1', 'DigitalOcean', 50.1109, 8.6821, 'Germany', 'Frankfurt', 'DigitalOcean FRA1 datacenter'),
                ('do-tor1', 'Toronto 1', 'DigitalOcean', 43.6532, -79.3832, 'Canada', 'Toronto', 'DigitalOcean TOR1 datacenter'),
                ('do-blr1', 'Bangalore 1', 'DigitalOcean', 12.9716, 77.5946, 'India', 'Bangalore', 'DigitalOcean BLR1 datacenter'),
                ('do-syd1', 'Sydney 1', 'DigitalOcean', -33.8688, 151.2093, 'Australia', 'Sydney', 'DigitalOcean SYD1 datacenter'),

                # AWS regions
                ('us-east-1', 'US East (N. Virginia)', 'AWS', 38.9072, -77.0369, 'USA', 'Virginia', 'AWS US East 1'),
                ('us-east-2', 'US East (Ohio)', 'AWS', 39.9612, -82.9988, 'USA', 'Ohio', 'AWS US East 2'),
                ('us-west-1', 'US West (N. California)', 'AWS', 37.7749, -122.4194, 'USA', 'California', 'AWS US West 1'),
                ('us-west-2', 'US West (Oregon)', 'AWS', 45.5152, -122.6784, 'USA', 'Oregon', 'AWS US West 2'),
                ('eu-west-1', 'EU (Ireland)', 'AWS', 53.3498, -6.2603, 'Ireland', 'Dublin', 'AWS EU West 1'),
                ('eu-central-1', 'EU (Frankfurt)', 'AWS', 50.1109, 8.6821, 'Germany', 'Frankfurt', 'AWS EU Central 1'),
                ('ap-southeast-1', 'Asia Pacific (Singapore)', 'AWS', 1.3521, 103.8198, 'Singapore', 'Singapore', 'AWS AP Southeast 1'),
                ('ap-northeast-1', 'Asia Pacific (Tokyo)', 'AWS', 35.6762, 139.6503, 'Japan', 'Tokyo', 'AWS AP Northeast 1'),

                # Google Cloud regions
                ('us-central1', 'Iowa', 'Google Cloud', 41.2619, -95.8608, 'USA', 'Iowa', 'Google Cloud us-central1'),
                ('us-east4', 'Northern Virginia', 'Google Cloud', 38.9072, -77.0369, 'USA', 'Virginia', 'Google Cloud us-east4'),
                ('europe-west1', 'Belgium', 'Google Cloud', 50.4501, 3.8196, 'Belgium', 'St. Ghislain', 'Google Cloud europe-west1'),
                ('europe-west2', 'London', 'Google Cloud', 51.5074, -0.1278, 'UK', 'London', 'Google Cloud europe-west2'),
                ('asia-east1', 'Taiwan', 'Google Cloud', 24.0511, 120.5135, 'Taiwan', 'Changhua County', 'Google Cloud asia-east1'),
            ]

            await conn.executemany("""
                INSERT INTO locations (region_code, region_name, cloud_provider, latitude, longitude, country, city, description)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                ON CONFLICT (region_code) DO NOTHING
            """, locations_data)

            final_count = await conn.fetchval("SELECT COUNT(*) FROM locations")
            print(f"✓ Inserted {final_count} location records")
        else:
            print(f"✓ locations table already contains {count} records")

        await conn.close()
        print("\n✅ Database setup complete!")
        return True

    except Exception as e:
        print(f"\n❌ Error setting up database: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(setup_database())
    exit(0 if success else 1)
