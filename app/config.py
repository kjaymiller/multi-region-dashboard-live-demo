"""Configuration and region definitions for the Multi-Region PostgreSQL Dashboard."""

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class RegionConfig:
    """Configuration for a database region."""
    id: str
    name: str
    env_key: str
    latitude: float
    longitude: float

    @property
    def dsn(self) -> str | None:
        """Get the connection string from environment variables."""
        return os.getenv(self.env_key)


REGIONS: dict[str, RegionConfig] = {
    "us-east": RegionConfig(
        id="us-east",
        name="US East (Virginia)",
        env_key="AIVEN_PG_US_EAST",
        latitude=37.4316,
        longitude=-78.6569,
    ),
    "eu-west": RegionConfig(
        id="eu-west",
        name="EU West (Ireland)",
        env_key="AIVEN_PG_EU_WEST",
        latitude=53.1424,
        longitude=-7.6921,
    ),
    "asia-pacific": RegionConfig(
        id="asia-pacific",
        name="Asia Pacific (Singapore)",
        env_key="AIVEN_PG_ASIA_PACIFIC",
        latitude=1.3521,
        longitude=103.8198,
    ),
}


def get_region(region_id: str) -> RegionConfig | None:
    """Get a region configuration by ID."""
    return REGIONS.get(region_id)


def get_all_regions() -> list[RegionConfig]:
    """Get all configured regions."""
    return list(REGIONS.values())


def get_dsn(region_id: str) -> str | None:
    """Get the connection string for a region."""
    region = get_region(region_id)
    return region.dsn if region else None


# LaunchDarkly configuration
LAUNCHDARKLY_SDK_KEY = os.getenv("LAUNCHDARKLY_SDK_KEY", "")
