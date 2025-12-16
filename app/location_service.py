"""Location service for calculating geographic distances and latency predictions."""

import math
from typing import TypedDict

import asyncpg

from app.config import get_dsn


class Location(TypedDict):
    """Geographic location coordinates."""

    lat: float
    lon: float
    city: str
    country: str


# Mapping of cloud provider regions to geographic coordinates
REGION_LOCATIONS: dict[str, Location] = {
    # DigitalOcean regions
    "do-nyc1": {"lat": 40.7128, "lon": -74.0060, "city": "New York", "country": "USA"},
    "do-nyc2": {"lat": 40.7128, "lon": -74.0060, "city": "New York", "country": "USA"},
    "do-nyc3": {"lat": 40.7128, "lon": -74.0060, "city": "New York", "country": "USA"},
    "do-sfo1": {"lat": 37.7749, "lon": -122.4194, "city": "San Francisco", "country": "USA"},
    "do-sfo2": {"lat": 37.7749, "lon": -122.4194, "city": "San Francisco", "country": "USA"},
    "do-sfo3": {"lat": 37.7749, "lon": -122.4194, "city": "San Francisco", "country": "USA"},
    "do-ams2": {"lat": 52.3676, "lon": 4.9041, "city": "Amsterdam", "country": "Netherlands"},
    "do-ams3": {"lat": 52.3676, "lon": 4.9041, "city": "Amsterdam", "country": "Netherlands"},
    "do-sgp1": {"lat": 1.3521, "lon": 103.8198, "city": "Singapore", "country": "Singapore"},
    "do-lon1": {"lat": 51.5074, "lon": -0.1278, "city": "London", "country": "UK"},
    "do-fra1": {"lat": 50.1109, "lon": 8.6821, "city": "Frankfurt", "country": "Germany"},
    "do-tor1": {"lat": 43.6532, "lon": -79.3832, "city": "Toronto", "country": "Canada"},
    "do-blr1": {"lat": 12.9716, "lon": 77.5946, "city": "Bangalore", "country": "India"},
    "do-syd1": {"lat": -33.8688, "lon": 151.2093, "city": "Sydney", "country": "Australia"},
    # AWS regions
    "us-east-1": {"lat": 38.9072, "lon": -77.0369, "city": "Virginia", "country": "USA"},
    "us-east-2": {"lat": 39.9612, "lon": -82.9988, "city": "Ohio", "country": "USA"},
    "us-west-1": {"lat": 37.7749, "lon": -122.4194, "city": "California", "country": "USA"},
    "us-west-2": {"lat": 45.5152, "lon": -122.6784, "city": "Oregon", "country": "USA"},
    "eu-west-1": {"lat": 53.3498, "lon": -6.2603, "city": "Ireland", "country": "Ireland"},
    "eu-central-1": {"lat": 50.1109, "lon": 8.6821, "city": "Frankfurt", "country": "Germany"},
    "ap-southeast-1": {"lat": 1.3521, "lon": 103.8198, "city": "Singapore", "country": "Singapore"},
    "ap-northeast-1": {"lat": 35.6762, "lon": 139.6503, "city": "Tokyo", "country": "Japan"},
    # Google Cloud regions
    "us-central1": {"lat": 41.2619, "lon": -95.8608, "city": "Iowa", "country": "USA"},
    "us-east4": {"lat": 38.9072, "lon": -77.0369, "city": "Virginia", "country": "USA"},
    "europe-west1": {"lat": 50.4501, "lon": 3.8196, "city": "Belgium", "country": "Belgium"},
    "europe-west2": {"lat": 51.5074, "lon": -0.1278, "city": "London", "country": "UK"},
    "asia-east1": {"lat": 24.0511, "lon": 120.5135, "city": "Taiwan", "country": "Taiwan"},
}


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance between two points on Earth.

    Args:
        lat1: Latitude of point 1 in degrees
        lon1: Longitude of point 1 in degrees
        lat2: Latitude of point 2 in degrees
        lon2: Longitude of point 2 in degrees

    Returns:
        Distance in kilometers
    """
    # Convert to radians
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    # Haversine formula
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad

    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))

    # Earth's radius in kilometers
    radius = 6371.0

    return radius * c


async def get_region_location_from_db(region: str | None) -> Location | None:
    """Get the geographic location for a given cloud region from database."""
    if not region:
        return None

    dsn = get_dsn()
    if not dsn:
        # Fallback to hardcoded locations
        return REGION_LOCATIONS.get(region.lower())

    try:
        conn = await asyncpg.connect(dsn)
        row = await conn.fetchrow(
            """
            SELECT latitude, longitude, city, country
            FROM locations
            WHERE LOWER(region_code) = LOWER($1) AND is_active = true
            LIMIT 1
        """,
            region,
        )
        await conn.close()

        if row:
            return {
                "lat": float(row["latitude"]),
                "lon": float(row["longitude"]),
                "city": row["city"] or "",
                "country": row["country"] or "",
            }

        # Fallback to hardcoded if not found in database
        return REGION_LOCATIONS.get(region.lower())

    except Exception:
        # Fallback to hardcoded locations on error
        return REGION_LOCATIONS.get(region.lower())


def get_region_location(region: str | None) -> Location | None:
    """Get the geographic location for a given cloud region (synchronous, uses hardcoded data)."""
    if not region:
        return None
    return REGION_LOCATIONS.get(region.lower())


async def calculate_distance_to_region_async(
    user_lat: float, user_lon: float, region: str | None
) -> float | None:
    """
    Calculate the distance from user location to a database region (async version using database).

    Args:
        user_lat: User's latitude
        user_lon: User's longitude
        region: Cloud provider region code

    Returns:
        Distance in kilometers, or None if region is unknown
    """
    region_loc = await get_region_location_from_db(region)
    if not region_loc:
        return None

    return haversine_distance(user_lat, user_lon, region_loc["lat"], region_loc["lon"])


def calculate_distance_to_region(
    user_lat: float, user_lon: float, region: str | None
) -> float | None:
    """
    Calculate the distance from user location to a database region (synchronous, uses hardcoded data).

    Args:
        user_lat: User's latitude
        user_lon: User's longitude
        region: Cloud provider region code

    Returns:
        Distance in kilometers, or None if region is unknown
    """
    region_loc = get_region_location(region)
    if not region_loc:
        return None

    return haversine_distance(user_lat, user_lon, region_loc["lat"], region_loc["lon"])


def estimate_latency_from_distance(distance_km: float) -> float:
    """
    Estimate network latency based on geographic distance.

    This is a rough estimate using:
    - Speed of light in fiber: ~200,000 km/s
    - Round trip time (RTT): distance * 2
    - Additional overhead: ~20ms for processing

    Args:
        distance_km: Distance in kilometers

    Returns:
        Estimated latency in milliseconds
    """
    # Speed of light in fiber optic cable (roughly 2/3 speed of light in vacuum)
    speed_km_per_ms = 200  # km/ms

    # Calculate round-trip time
    rtt_ms = (distance_km * 2) / speed_km_per_ms

    # Add base overhead for processing, routing, etc.
    overhead_ms = 20

    return round(rtt_ms + overhead_ms, 2)
