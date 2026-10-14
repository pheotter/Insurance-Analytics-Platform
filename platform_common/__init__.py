"""Shared infrastructure used by local platform components."""

from .snowflake import SnowflakeSettings, connect_snowflake, validate_identifier

__all__ = ["SnowflakeSettings", "connect_snowflake", "validate_identifier"]
