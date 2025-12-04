"""LaunchDarkly feature flag integration."""

import ldclient
from ldclient import Context
from ldclient.config import Config

from app.config import LAUNCHDARKLY_SDK_KEY

# Initialize LaunchDarkly client
_ld_client: ldclient.LDClient | None = None


def init_launchdarkly() -> None:
    """Initialize the LaunchDarkly client."""
    global _ld_client
    if LAUNCHDARKLY_SDK_KEY:
        ldclient.set_config(Config(LAUNCHDARKLY_SDK_KEY))
        _ld_client = ldclient.get()


def close_launchdarkly() -> None:
    """Close the LaunchDarkly client connection."""
    global _ld_client
    if _ld_client:
        _ld_client.close()
        _ld_client = None


def get_user_context(user_key: str, **attributes) -> Context:
    """Create a LaunchDarkly context for a user."""
    builder = Context.builder(user_key)
    for key, value in attributes.items():
        builder.set(key, value)
    return builder.build()


def is_region_enabled(region_id: str, user_key: str = "anonymous") -> bool:
    """Check if a specific region is enabled for the user."""
    if not _ld_client:
        return True  # Default to enabled if LaunchDarkly is not configured

    context = get_user_context(user_key)
    flag_key = f"region-{region_id}-enabled"
    return _ld_client.variation(flag_key, context, True)


def is_feature_enabled(feature_key: str, user_key: str = "anonymous") -> bool:
    """Check if a feature is enabled for the user."""
    if not _ld_client:
        return True  # Default to enabled if LaunchDarkly is not configured

    context = get_user_context(user_key)
    return _ld_client.variation(feature_key, context, True)


def get_refresh_interval(user_key: str = "anonymous") -> int:
    """Get the dashboard auto-refresh interval in seconds."""
    if not _ld_client:
        return 30  # Default 30 seconds

    context = get_user_context(user_key)
    return _ld_client.variation("dashboard-refresh-seconds", context, 30)


def is_health_checks_enabled(user_key: str = "anonymous") -> bool:
    """Check if health checks feature is enabled."""
    return is_feature_enabled("enable-health-checks", user_key)


def is_load_testing_enabled(user_key: str = "anonymous") -> bool:
    """Check if load testing feature is enabled."""
    return is_feature_enabled("enable-load-testing", user_key)


def is_test_all_regions_enabled(user_key: str = "anonymous") -> bool:
    """Check if test all regions feature is enabled."""
    return is_feature_enabled("enable-test-all-regions", user_key)


def get_enabled_regions(user_key: str = "anonymous") -> list[str]:
    """Get list of enabled region IDs for a user."""
    from app.config import REGIONS

    enabled = []
    for region_id in REGIONS.keys():
        if is_region_enabled(region_id, user_key):
            enabled.append(region_id)
    return enabled
