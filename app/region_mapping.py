"""Region mapping data and utilities for geographic visualization."""


# Region coordinates mapping
REGION_COORDINATES: dict[str, dict[str, float]] = {
    # AWS regions
    "us-east-1": {"lat": 39.0458, "lng": -77.6413},  # Northern Virginia
    "us-east-2": {"lat": 40.4173, "lng": -82.9071},  # Ohio
    "us-west-1": {"lat": 37.7749, "lng": -122.4194}, # N. California
    "us-west-2": {"lat": 45.5152, "lng": -122.6784}, # Oregon
    "us-central-1": {"lat": 41.8781, "lng": -87.6298}, # Illinois
    "ca-central-1": {"lat": 45.4215, "lng": -75.6972}, # Canada
    "eu-west-1": {"lat": 53.4084, "lng": -8.2439},   # Ireland
    "eu-west-2": {"lat": 51.5074, "lng": -0.1278},   # London
    "eu-central-1": {"lat": 50.1109, "lng": 8.6821},  # Frankfurt
    "eu-north-1": {"lat": 59.3293, "lng": 18.0686},  # Stockholm
    "eu-south-1": {"lat": 41.9028, "lng": 12.4964},  # Italy
    "ap-southeast-1": {"lat": 1.3521, "lng": 103.8198}, # Singapore
    "ap-southeast-2": {"lat": -33.8688, "lng": 151.2093}, # Sydney
    "ap-northeast-1": {"lat": 35.6762, "lng": 139.6503}, # Tokyo
    "ap-northeast-2": {"lat": 37.5665, "lng": 126.9780}, # Seoul
    "ap-south-1": {"lat": 19.0760, "lng": 72.8777},   # Mumbai
    "me-south-1": {"lat": 25.2048, "lng": 55.2708},  # Bahrain
    "af-south-1": {"lat": -26.2041, "lng": 28.0473}, # Cape Town
    "sa-east-1": {"lat": -23.5505, "lng": -46.6333}, # São Paulo

    # GCP regions
    "us-central1": {"lat": 32.9466, "lng": -96.8308},  # Iowa
    "us-east1": {"lat": 33.7490, "lng": -84.3880},    # South Carolina
    "us-west1": {"lat": 37.7749, "lng": -122.4194},   # Oregon
    "us-west2": {"lat": 34.0522, "lng": -118.2437},   # Los Angeles
    "europe-west1": {"lat": 50.1109, "lng": 8.6821},  # Belgium
    "europe-west2": {"lat": 51.5074, "lng": -0.1278},  # London
    "europe-west3": {"lat": 48.8566, "lng": 2.3522},    # Frankfurt
    "europe-west4": {"lat": 52.5200, "lng": 13.4050},   # Netherlands
    "asia-southeast1": {"lat": 1.3521, "lng": 103.8198}, # Singapore
    "asia-northeast1": {"lat": 35.6762, "lng": 139.6503}, # Tokyo
    "asia-northeast2": {"lat": 37.5665, "lng": 126.9780}, # Seoul
    "asia-south1": {"lat": 19.0760, "lng": 72.8777},   # Mumbai
    "australia-southeast1": {"lat": -33.8688, "lng": 151.2093}, # Sydney

    # Azure regions
    "eastus": {"lat": 37.3719, "lng": -79.8164},     # Virginia
    "westus": {"lat": 37.7749, "lng": -122.4194},    # California
    "centralus": {"lat": 41.8781, "lng": -87.6298},   # Iowa
    "westeurope": {"lat": 52.5200, "lng": 13.4050},   # Netherlands
    "northeurope": {"lat": 53.4084, "lng": -8.2439},  # Ireland
    "southeastasia": {"lat": 1.3521, "lng": 103.8198}, # Singapore
    "eastasia": {"lat": 22.3193, "lng": 114.1694},    # Hong Kong
    "australiaeast": {"lat": -33.8688, "lng": 151.2093}, # Sydney
    "brazilsouth": {"lat": -23.5505, "lng": -46.6333}, # São Paulo

    # Aiven regions
    "aws-eu-west-1": {"lat": 53.4084, "lng": -8.2439},  # Ireland
    "aws-us-east-1": {"lat": 39.0458, "lng": -77.6413},  # Virginia
    "aws-us-west-2": {"lat": 45.5152, "lng": -122.6784}, # Oregon
    "gcp-europe-west1": {"lat": 50.1109, "lng": 8.6821},  # Belgium
    "gcp-us-central1": {"lat": 32.9466, "lng": -96.8308},  # Iowa
    "do-nyc1": {"lat": 40.7128, "lng": -74.0060},     # NYC
    "do-ams1": {"lat": 52.5200, "lng": 13.4050},      # Amsterdam
}

# Cloud provider colors
CLOUD_COLORS = {
    "AWS": "#ff9900",
    "GCP": "#4285f4",
    "Azure": "#0078d4",
    "Aiven": "#ff3554",
    "DigitalOcean": "#0069ff",
    "Other": "#6c757d"
}


def get_region_coordinates(region: str) -> dict[str, float] | None:
    """Get coordinates for a given region."""
    # Normalize region name (case insensitive)
    normalized_region = region.lower()

    for key, coords in REGION_COORDINATES.items():
        if key.lower() == normalized_region:
            return coords

    # Try to find partial matches
    for key, coords in REGION_COORDINATES.items():
        if normalized_region in key.lower() or key.lower() in normalized_region:
            return coords

    return None


def get_cloud_color(provider: str) -> str:
    """Get color for cloud provider."""
    return CLOUD_COLORS.get(provider, CLOUD_COLORS["Other"])


def estimate_latency_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate estimated latency based on geographic distance."""
    from math import asin, cos, radians, sin, sqrt

    # Haversine formula for distance
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))

    # Earth's radius in km
    distance_km = 6371 * c

    # Simple latency estimation: 1ms per 200km for fiber optics
    # This is a rough approximation for underwater/underground cables
    estimated_latency_ms = distance_km / 200

    return round(estimated_latency_ms, 1)
