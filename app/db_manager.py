"""Secure database connection management for multiple PostgreSQL databases."""

import base64
import json
import os
import secrets
from dataclasses import dataclass

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


@dataclass
class DatabaseConnection:
    """Represents a database connection configuration."""

    id: str
    name: str
    host: str
    port: int
    database: str
    username: str
    password: str  # Encrypted
    ssl_mode: str = "require"
    region: str | None = None
    cloud_provider: str | None = None
    is_active: bool = True
    created_at: str | None = None

    @property
    def dsn(self) -> str:
        """Generate the database connection string."""
        return (
            f"postgresql://{self.username}:{self.password}@"
            f"{self.host}:{self.port}/{self.database}?ssl={self.ssl_mode}"
        )


class DatabaseManager:
    """Manages secure database connections with encrypted storage."""

    def __init__(self, storage_path: str = ".db_connections"):
        self.storage_path = storage_path
        self._key: bytes | None = None
        self._cipher: Fernet | None = None
        self._load_key()

    def _load_key(self) -> None:
        """Load or create encryption key."""
        key_file = os.path.join(self.storage_path, ".key")

        if os.path.exists(key_file):
            with open(key_file, "rb") as f:
                self._key = f.read()
        else:
            # Generate a new key with PBKDF2
            password = os.getenv("DB_MANAGER_PASSWORD", "default-password-change-me")
            salt = os.urandom(16)
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            self._key = base64.urlsafe_b64encode(kdf.derive(password.encode()))

            os.makedirs(self.storage_path, exist_ok=True)
            with open(key_file, "wb") as f:
                f.write(self._key)

        self._cipher = Fernet(self._key)

    def _encrypt(self, data: str) -> str:
        """Encrypt sensitive data."""
        if not self._cipher:
            raise RuntimeError("Cipher not initialized")
        return self._cipher.encrypt(data.encode()).decode()

    def _decrypt(self, encrypted_data: str) -> str:
        """Decrypt sensitive data."""
        if not self._cipher:
            raise RuntimeError("Cipher not initialized")
        return self._cipher.decrypt(encrypted_data.encode()).decode()

    def save_connection(self, connection: DatabaseConnection) -> bool:
        """Save a database connection with encrypted credentials."""
        try:
            # Encrypt the password
            encrypted_password = self._encrypt(connection.password)
            connection_data = {
                "id": connection.id,
                "name": connection.name,
                "host": connection.host,
                "port": connection.port,
                "database": connection.database,
                "username": connection.username,
                "password": encrypted_password,
                "ssl_mode": connection.ssl_mode,
                "region": connection.region,
                "cloud_provider": connection.cloud_provider,
                "is_active": connection.is_active,
                "created_at": connection.created_at,
            }

            # Load existing connections
            connections = self.load_connections()
            connections[connection.id] = connection_data

            # Save to file
            os.makedirs(self.storage_path, exist_ok=True)
            with open(os.path.join(self.storage_path, "connections.json"), "w") as f:
                json.dump(connections, f, indent=2)

            return True
        except Exception:
            return False

    def load_connections(self) -> dict[str, dict]:
        """Load all database connections and decrypt credentials."""
        connections_file = os.path.join(self.storage_path, "connections.json")

        if not os.path.exists(connections_file):
            return {}

        try:
            with open(connections_file) as f:
                data = json.load(f)

            # Decrypt passwords
            for _conn_id, conn_data in data.items():
                if "password" in conn_data:
                    conn_data["password"] = self._decrypt(conn_data["password"])

            return data
        except Exception:
            return {}

    def get_connection(self, connection_id: str) -> DatabaseConnection | None:
        """Get a specific database connection."""
        connections = self.load_connections()

        if connection_id not in connections:
            return None

        data = connections[connection_id]
        return DatabaseConnection(**data)

    def delete_connection(self, connection_id: str) -> bool:
        """Delete a database connection."""
        try:
            connections = self.load_connections()

            if connection_id in connections:
                del connections[connection_id]

                with open(os.path.join(self.storage_path, "connections.json"), "w") as f:
                    json.dump(connections, f, indent=2)

                return True

            return False
        except Exception:
            return False

    def test_connection(self, connection: DatabaseConnection) -> dict:
        """Test a database connection."""
        import asyncio
        import time

        import asyncpg

        async def _test():
            try:
                start = time.perf_counter()

                # Use SSL for remote connections, disable for local development
                ssl_mode = (
                    "require"
                    if not any(
                        local_host in connection.host.lower()
                        for local_host in ["localhost", "127.0.0.1", "postgres:"]
                    )
                    else None
                )

                conn = await asyncpg.connect(
                    dsn=connection.dsn,
                    ssl=ssl_mode
                )

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

        return asyncio.run(_test())

    def get_all_connections(self) -> list[DatabaseConnection]:
        """Get all active database connections."""
        connections = self.load_connections()

        active_connections = []
        for conn_data in connections.values():
            if conn_data.get("is_active", True):
                active_connections.append(DatabaseConnection(**conn_data))

        return active_connections

    def generate_connection_id(self) -> str:
        """Generate a unique connection ID."""
        return f"db_{secrets.token_hex(8)}"


# Global database manager instance
db_manager = DatabaseManager()
