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


@dataclass
class ChatConfig:
    """Configuration for AI chat functionality."""
    
    enabled: bool = True
    base_url: str = "http://localhost:11434"
    model: str = "llama3.2:latest"
    
    def __post_init__(self) -> None:
        """Load configuration from environment variables."""
        self.enabled = os.getenv("CHAT_ENABLED", "true").lower() == "true"
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model = os.getenv("OLLAMA_MODEL", "llama3.2:latest")


# Single database configuration
DATABASE = DatabaseConfig(
    name="PostgreSQL Database",
    env_key="DATABASE_URL",
)

# Chat configuration
CHAT = ChatConfig()


def get_database() -> DatabaseConfig:
    """Get the database configuration."""
    return DATABASE


def get_dsn() -> str | None:
    """Get the database connection string."""
    return DATABASE.dsn


def get_chat_config() -> ChatConfig:
    """Get the chat configuration."""
    return CHAT
