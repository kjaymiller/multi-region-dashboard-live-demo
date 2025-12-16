"""Secure database connection management using PostgreSQL backend."""

import secrets
from dataclasses import dataclass, field

import asyncpg
import bcrypt

from app.config import get_database


@dataclass
class DatabaseConnection:
    """Represents a database connection configuration."""

    id: str
    name: str
    host: str
    port: int
    database: str
    username: str
    password: str | None = field(repr=False, default=None)  # Plain text for input, not stored
    password_hash: str | None = field(repr=False, default=None)    # Hashed password
    salt: str | None = field(repr=False, default=None)        # Salt for password
    ssl_mode: str = "require"
    region: str | None = None
    cloud_provider: str | None = None
    is_active: bool = True
    created_at: str | None = None
    updated_at: str | None = None

    @property
    def dsn(self) -> str:
        """Generate the database connection string for testing (password not included)."""
        return (
            f"postgresql://{self.username}:*****@"
            f"{self.host}:{self.port}/{self.database}?ssl={self.ssl_mode}"
        )


class DatabaseManager:
    """Manages secure database connections with PostgreSQL backend."""

    def __init__(self):
        self._pool = None

    async def _get_pool(self):
        """Get or create database connection pool."""
        if self._pool is None:
            self._pool = await asyncpg.create_pool(get_database().dsn)
        return self._pool

    async def save_connection(self, connection: DatabaseConnection) -> bool:
        """Save a database connection with hashed password."""
        try:
            pool = await self._get_pool()

            # Hash password with salt
            if not connection.password:
                raise ValueError("Password is required")
            salt = secrets.token_hex(16)
            password_hash = bcrypt.hashpw(
                connection.password.encode(),
                bcrypt.gensalt(rounds=12)  # Using bcrypt with rounds=12
            ).decode()

            async with pool.acquire() as conn:
                if connection.id and await self._connection_exists(connection.id):
                    # Update existing connection
                    await conn.execute("""
                        UPDATE database_connections 
                        SET name = $1, host = $2, port = $3, database = $4,
                            username = $5, password_hash = $6, salt = $7, 
                            ssl_mode = $8, region = $9, cloud_provider = $10,
                            is_active = $11, updated_at = CURRENT_TIMESTAMP
                        WHERE id = $12
                    """,
                        connection.name, connection.host, connection.port, connection.database,
                        connection.username, password_hash, salt, connection.ssl_mode,
                        connection.region, connection.cloud_provider, connection.is_active,
                        connection.id
                    )
                else:
                    # Create new connection
                    conn_id = connection.id or f"db_{secrets.token_hex(8)}"
                    await conn.execute("""
                        INSERT INTO database_connections 
                        (id, name, host, port, database, username, password_hash, 
                         salt, ssl_mode, region, cloud_provider, is_active)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                    """,
                        conn_id, connection.name, connection.host, connection.port,
                        connection.database, connection.username, password_hash, salt,
                        connection.ssl_mode, connection.region, connection.cloud_provider,
                        connection.is_active
                    )
                    connection.id = conn_id

                # Update connection object with generated hash and salt
                connection.password_hash = password_hash
                connection.salt = salt

            return True
        except Exception:
            return False

    async def _connection_exists(self, connection_id: str) -> bool:
        """Check if connection exists."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            result = await conn.fetchval(
                "SELECT 1 FROM database_connections WHERE id = $1",
                connection_id
            )
            return result is not None

    async def get_connection(self, connection_id: str) -> DatabaseConnection | None:
        """Get a specific database connection."""
        try:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT id, name, host, port, database_name, username, 
                           password_hash, salt, ssl_mode, region, cloud_provider,
                           is_active, created_at, updated_at
                    FROM database_connections 
                    WHERE id = $1 AND is_active = true
                """, connection_id)

                if row:
                    return DatabaseConnection(
                        id=row['id'],
                        name=row['name'],
                        host=row['host'],
                        port=row['port'],
                        database=row['database_name'],
                        username=row['username'],
                        password_hash=row['password_hash'],
                        salt=row['salt'],
                        ssl_mode=row['ssl_mode'],
                        region=row['region'],
                        cloud_provider=row['cloud_provider'],
                        is_active=row['is_active'],
                        created_at=row['created_at'].isoformat() if row['created_at'] else None,
                        updated_at=row['updated_at'].isoformat() if row['updated_at'] else None,
                    )
                return None
        except Exception:
            return None

    async def delete_connection(self, connection_id: str) -> bool:
        """Delete a database connection."""
        try:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                await conn.execute(
                    "DELETE FROM database_connections WHERE id = $1",
                    connection_id
                )
            return True
        except Exception:
            return False

    async def get_all_connections(self) -> list[DatabaseConnection]:
        """Get all active database connections."""
        try:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT id, name, host, port, database, username,
                           password_hash, salt, ssl_mode, region, cloud_provider,
                           is_active, created_at, updated_at
                    FROM database_connections 
                    WHERE is_active = true
                    ORDER BY created_at DESC
                """)

                connections = []
                for row in rows:
                    connections.append(DatabaseConnection(
                        id=row['id'],
                        name=row['name'],
                        host=row['host'],
                        port=row['port'],
                        database=row['database'],
                        username=row['username'],
                        password_hash=row['password_hash'],
                        salt=row['salt'],
                        ssl_mode=row['ssl_mode'],
                        region=row['region'],
                        cloud_provider=row['cloud_provider'],
                        is_active=row['is_active'],
                        created_at=row['created_at'].isoformat() if row['created_at'] else None,
                        updated_at=row['updated_at'].isoformat() if row['updated_at'] else None,
                    ))

                return connections
        except Exception:
            return []

    async def test_connection_with_password(self, connection: DatabaseConnection, password: str) -> dict:
        """Test a database connection using provided password."""
        import time

        async def _test():
            try:
                start = time.perf_counter()

                # Use SSL for remote connections, disable for local development
                ssl_mode = (
                    "require"
                    if not any(
                        local_host in connection.host.lower()
                        for local_host in ["localhost", "127.0.0.1", "postgres"]
                    )
                    else None
                )

                # Build DSN with actual password for testing
                if ssl_mode:
                    test_dsn = (
                        f"postgresql://{connection.username}:{password}@"
                        f"{connection.host}:{connection.port}/{connection.database}?ssl=require"
                    )
                    conn = await asyncpg.connect(test_dsn, ssl=True)
                else:
                    test_dsn = (
                        f"postgresql://{connection.username}:{password}@"
                        f"{connection.host}:{connection.port}/{connection.database}"
                    )
                    conn = await asyncpg.connect(test_dsn, ssl=False)

                result = await conn.fetchrow("""
                    SELECT
                        inet_server_addr()::text AS server_ip,
                        pg_backend_pid() AS backend_pid,
                        version() AS pg_version
                """)
                latency_ms = (time.perf_counter() - start) * 1000

                await conn.close()

                return {
                    "success": True,
                    "server_ip": result["server_ip"],
                    "backend_pid": result["backend_pid"],
                    "pg_version": result["pg_version"],
                    "latency_ms": round(latency_ms, 2),
                }
            except Exception as e:
                return {"success": False, "error": str(e)}

        return await _test()

    async def verify_password(self, connection: DatabaseConnection, password: str) -> bool:
        """Verify password against stored hash."""
        if not connection.password_hash:
            return False
        return bcrypt.checkpw(password.encode(), connection.password_hash.encode())

    def generate_connection_id(self) -> str:
        """Generate a unique connection ID."""
        return f"db_{secrets.token_hex(8)}"

    async def close(self):
        """Close database connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None


# Global database manager instance
db_manager = DatabaseManager()
