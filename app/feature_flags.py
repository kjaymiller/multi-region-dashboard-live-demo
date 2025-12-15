"""Simple feature flag implementation without external dependencies."""

from app.config import REGIONS


def is_region_enabled(region_id: str, user_key: str = "anonymous") -> bool:
    """Check if a specific region is enabled for the user."""
    # All regions enabled by default
    return region_id in REGIONS


def is_feature_enabled(feature_key: str, user_key: str = "anonymous") -> bool:
    """Check if a feature is enabled for the user."""
    # All features enabled by default
    return True


def get_refresh_interval(user_key: str = "anonymous") -> int:
    """Get the dashboard auto-refresh interval in seconds."""
    # Default 30 seconds
    return 30


def is_health_checks_enabled(user_key: str = "anonymous") -> bool:
    """Check if health checks feature is enabled."""
    return is_feature_enabled("enable-health-checks", user_key)


def is_load_testing_enabled(user_key: str = "anonymous") -> bool:
    """Check if load testing feature is enabled."""
    return is_feature_enabled("enable-load-testing", user_key)


def is_test_all_regions_enabled(user_key: str = "anonymous") -> bool:
    """Check if test all regions feature is enabled."""
    return is_feature_enabled("enable-test-all-regions", user_key)


def is_chatbot_enabled(user_key: str = "anonymous") -> bool:
    """Check if chatbot feature is enabled."""
    return is_feature_enabled("dashboard-chatbot-enabled", user_key)


def is_refresh_table_button_enabled(user_key: str = "anonymous") -> bool:
    """Check if refresh table button is enabled."""
    return is_feature_enabled("refresh-table-button", user_key)


def track_chatbot_metric(
    event_key: str,
    user_key: str = "anonymous",
    metric_value: float | None = None,
    **custom_attributes
) -> None:
    """
    Track a chatbot metric (no-op without LaunchDarkly).
    
    Args:
        event_key: The event key (e.g., 'chatbot.connection.status')
        user_key: User identifier for the context
        metric_value: Numeric value for the metric
        **custom_attributes: Additional attributes to include
    """
    # No-op without LaunchDarkly
    pass


def get_enabled_regions(user_key: str = "anonymous") -> list[str]:
    """Get list of enabled region IDs for a user."""
    return list(REGIONS.keys())