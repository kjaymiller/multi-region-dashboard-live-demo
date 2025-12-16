"""Secure database connection management using PostgreSQL backend."""

import base64
import os
from dataclasses import dataclass, field

import asyncpg
import bcrypt
from cryptography.fernet import Fernet

from app.config import get_database


@dataclass
class DatabaseConnection:
    """Represents a database connection configuration."""

    id: int
    name: str
    host: str
    port: int
    database: str
    username: str
    password: str | None = field(repr=False, default=None)  # Plain text for input, not stored
    password_hash: str | None = field(repr=False, default=None)  # Hashed password
    salt: str | None = field(repr=False, default=None)  # Salt for password
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
        self._cipher = None

    def _get_cipher(self) -> Fernet:
        """Get or create the encryption cipher."""
        if self._cipher is None:
            # Get encryption key from environment or generate one
            encryption_key = os.getenv("DB_PASSWORD_ENCRYPTION_KEY")
            if not encryption_key:
                # Generate a new key and warn user
                encryption_key = Fernet.generate_key().decode()
                import warnings

                warnings.warn(
                    f"No DB_PASSWORD_ENCRYPTION_KEY found in environment. "
                    f"Generated temporary key: {encryption_key}\n"
                    f"Add this to your .env file: DB_PASSWORD_ENCRYPTION_KEY={encryption_key}",
                    stacklevel=2,
                )

            # Ensure key is in bytes
            if isinstance(encryption_key, str):
                encryption_key = encryption_key.encode()

            self._cipher = Fernet(encryption_key)
        return self._cipher

    def _encrypt_password(self, password: str) -> str:
        """Encrypt a password for storage."""
        cipher = self._get_cipher()
        encrypted = cipher.encrypt(password.encode())
        return base64.b64encode(encrypted).decode()

    def _decrypt_password(self, encrypted_password: str) -> str:
        """Decrypt a stored password."""
        cipher = self._get_cipher()
        encrypted = base64.b64decode(encrypted_password.encode())
        decrypted = cipher.decrypt(encrypted)
        return decrypted.decode()

    async def _get_pool(self):
        """Get or create database connection pool."""
        if self._pool is None:
            self._pool = await asyncpg.create_pool(get_database().dsn)
        return self._pool

    async def save_connection(self, connection: DatabaseConnection) -> bool:
        """Save a database connection with encrypted password."""
        try:
            pool = await self._get_pool()

            # Encrypt password
            if not connection.password:
                raise ValueError("Password is required")

            encrypted_password = self._encrypt_password(connection.password)
            # Keep salt column for backward compatibility but don't use it
            salt = ""

            async with pool.acquire() as conn:
                if connection.id and await self._connection_exists(connection.id):
                    # Update existing connection
                    await conn.execute(
                        """
                        UPDATE database_connections
                        SET name = $1, host = $2, port = $3, database_name = $4,
                            username = $5, password_hash = $6, salt = $7,
                            ssl_mode = $8, region = $9, cloud_provider = $10,
                            is_active = $11, updated_at = CURRENT_TIMESTAMP
                        WHERE id = $12
                    """,
                        connection.name,
                        connection.host,
                        connection.port,
                        connection.database,
                        connection.username,
                        encrypted_password,
                        salt,
                        connection.ssl_mode,
                        connection.region,
                        connection.cloud_provider,
                        connection.is_active,
                        connection.id,
                    )
                else:
                    # Create new connection - let PostgreSQL auto-generate the ID
                    conn_id = await conn.fetchval(
                        """
                        INSERT INTO database_connections
                        (name, host, port, database_name, username, password_hash,
                         salt, ssl_mode, region, cloud_provider, is_active)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                        RETURNING id
                    """,
                        connection.name,
                        connection.host,
                        connection.port,
                        connection.database,
                        connection.username,
                        encrypted_password,
                        salt,
                        connection.ssl_mode,
                        connection.region,
                        connection.cloud_provider,
                        connection.is_active,
                    )
                    connection.id = conn_id

                # Update connection object with encrypted password
                connection.password_hash = encrypted_password
                connection.salt = salt

            return True
        except Exception:
            return False

    async def _connection_exists(self, connection_id: int) -> bool:
        """Check if connection exists."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            result = await conn.fetchval(
                "SELECT 1 FROM database_connections WHERE id = $1", connection_id
            )
            return result is not None

    async def get_connection(self, connection_id: int) -> DatabaseConnection | None:
        """Get a specific database connection with decrypted password."""
        try:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT id, name, host, port, database_name, username,
                           password_hash, salt, ssl_mode, region, cloud_provider,
                           is_active, created_at, updated_at
                    FROM database_connections
                    WHERE id = $1 AND is_active = true
                """,
                    connection_id,
                )

                if row:
                    # Decrypt password if present
                    password = None
                    if row["password_hash"]:
                        try:
                            password = self._decrypt_password(row["password_hash"])
                        except Exception:
                            # If decryption fails, password might be old bcrypt hash
                            # Leave it as None to maintain security
                            pass

                    return DatabaseConnection(
                        id=row["id"],
                        name=row["name"],
                        host=row["host"],
                        port=row["port"],
                        database=row["database_name"],
                        username=row["username"],
                        password=password,  # Now includes decrypted password
                        password_hash=row["password_hash"],
                        salt=row["salt"],
                        ssl_mode=row["ssl_mode"],
                        region=row["region"],
                        cloud_provider=row["cloud_provider"],
                        is_active=row["is_active"],
                        created_at=row["created_at"].isoformat() if row["created_at"] else None,
                        updated_at=row["updated_at"].isoformat() if row["updated_at"] else None,
                    )
                return None
        except Exception:
            return None

    async def delete_connection(self, connection_id: int) -> bool:
        """Delete a database connection."""
        try:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                await conn.execute("DELETE FROM database_connections WHERE id = $1", connection_id)
            return True
        except Exception:
            return False

    async def get_all_connections(self) -> list[DatabaseConnection]:
        """Get all active database connections with decrypted passwords."""
        try:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT id, name, host, port, database_name, username,
                           password_hash, salt, ssl_mode, region, cloud_provider,
                           is_active, created_at, updated_at
                    FROM database_connections
                    WHERE is_active = true
                    ORDER BY created_at DESC
                """
                )

                connections = []
                for row in rows:
                    # Decrypt password if present
                    password = None
                    if row["password_hash"]:
                        try:
                            password = self._decrypt_password(row["password_hash"])
                        except Exception:
                            # If decryption fails, password might be old bcrypt hash
                            # Leave it as None to maintain security
                            pass

                    connections.append(
                        DatabaseConnection(
                            id=row["id"],
                            name=row["name"],
                            host=row["host"],
                            port=row["port"],
                            database=row["database_name"],
                            username=row["username"],
                            password=password,  # Now includes decrypted password
                            password_hash=row["password_hash"],
                            salt=row["salt"],
                            ssl_mode=row["ssl_mode"],
                            region=row["region"],
                            cloud_provider=row["cloud_provider"],
                            is_active=row["is_active"],
                            created_at=row["created_at"].isoformat() if row["created_at"] else None,
                            updated_at=row["updated_at"].isoformat() if row["updated_at"] else None,
                        )
                    )

                return connections
        except Exception:
            return []

    async def test_connection(self, connection: DatabaseConnection) -> dict:
        """Test a database connection using the connection's decrypted password."""
        if not connection.password:
            return {"success": False, "error": "No password available for connection"}
        return await self.test_connection_with_password(connection, connection.password)

    async def test_connection_with_password(
        self, connection: DatabaseConnection, password: str
    ) -> dict:
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

                result = await conn.fetchrow(
                    """
                    SELECT
                        inet_server_addr()::text AS server_ip,
                        pg_backend_pid() AS backend_pid,
                        version() AS pg_version
                """
                )
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

    def generate_connection_id(self) -> int:
        """Generate a unique connection ID (not used - PostgreSQL auto-generates)."""
        # This method is deprecated - PostgreSQL auto-generates integer IDs
        raise NotImplementedError("Connection IDs are now auto-generated by PostgreSQL")

    async def close(self):
        """Close database connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None


# Global database manager instance
db_manager = DatabaseManager()
