"""Configuration for the PostgreSQL Dashboard."""

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass
class DatabaseConfig:
    """Configuration for the PostgreSQL database."""
    name: str
    env_key: str

    @property
    def dsn(self) -> str | None:
        """Get the connection string from environment variables."""
        return os.getenv(self.env_key)


# Single database configuration
DATABASE = DatabaseConfig(
    name="PostgreSQL Database",
    env_key="DATABASE_URL",
)


def get_database() -> DatabaseConfig:
    """Get the database configuration."""
    return DATABASE


def get_dsn() -> str | None:
    """Get the database connection string."""
    return DATABASE.dsn
