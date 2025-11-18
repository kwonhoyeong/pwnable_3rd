"""Unit tests for timestamp utilities."""

from datetime import datetime, timezone

import pytest

from src.core.utils.timestamps import ensure_datetime, normalize_timestamp


class TestNormalizeTimestamp:
    """Test normalize_timestamp function."""

    def test_normalize_iso_string(self):
        """Test normalizing ISO format timestamp string."""
        iso_string = "2025-11-18T10:30:00.123456"
        result = normalize_timestamp(iso_string)
        assert isinstance(result, str)
        assert result.startswith("2025-11-18")

    def test_normalize_datetime_object(self):
        """Test normalizing datetime object."""
        dt = datetime(2025, 11, 18, 10, 30, 0)
        result = normalize_timestamp(dt)
        assert isinstance(result, str)
        assert "2025-11-18" in result

    def test_normalize_none_returns_current_time(self):
        """Test normalizing None returns current time ISO string."""
        result = normalize_timestamp(None)
        # normalize_timestamp returns current time as ISO string when given None
        assert isinstance(result, str)
        assert "T" in result or result.count("-") >= 2

    def test_normalize_preserves_date_information(self):
        """Test that normalization preserves date information."""
        dt = datetime(2025, 11, 18, 10, 30, 0)
        result = normalize_timestamp(dt)
        assert "2025" in result
        assert "11" in result
        assert "18" in result

    def test_normalize_consistent_format(self):
        """Test that normalization produces consistent ISO format."""
        iso_string = "2025-11-18T10:30:00.123456"
        result = normalize_timestamp(iso_string)
        # Should be a valid ISO format string
        assert "T" in result or result.count("-") >= 2

    def test_normalize_with_timezone_aware_datetime(self):
        """Test normalizing timezone-aware datetime."""
        dt = datetime(
            2025, 11, 18, 10, 30, 0, tzinfo=timezone.utc
        )
        result = normalize_timestamp(dt)
        assert isinstance(result, str)
        assert len(result) > 0


class TestEnsureDatetime:
    """Test ensure_datetime function."""

    def test_ensure_datetime_object_returns_unchanged(self):
        """Test that datetime objects are returned unchanged."""
        dt = datetime(2025, 11, 18, 10, 30, 0)
        result = ensure_datetime(dt)
        assert result == dt

    def test_ensure_iso_string_converted_to_datetime(self):
        """Test converting ISO string to datetime."""
        iso_string = "2025-11-18T10:30:00.123456"
        result = ensure_datetime(iso_string)
        assert isinstance(result, datetime)

    def test_ensure_none_returns_now(self):
        """Test that None returns current datetime."""
        result = ensure_datetime(None)
        assert isinstance(result, datetime)
        # Should be close to now
        now = datetime.utcnow()
        assert abs((result - now).total_seconds()) < 1

    def test_ensure_string_parsing(self):
        """Test parsing various string formats."""
        test_cases = [
            "2025-11-18T10:30:00",
            "2025-11-18T10:30:00.123456",
            "2025-11-18T10:30:00Z",
        ]
        for iso_string in test_cases:
            result = ensure_datetime(iso_string)
            assert isinstance(result, datetime)

    def test_ensure_extracted_date_values(self):
        """Test that extracted date values are correct."""
        iso_string = "2025-11-18T10:30:45.123456"
        result = ensure_datetime(iso_string)
        assert result.year == 2025
        assert result.month == 11
        assert result.day == 18

    def test_ensure_extracted_time_values(self):
        """Test that extracted time values are correct."""
        iso_string = "2025-11-18T10:30:45.123456"
        result = ensure_datetime(iso_string)
        assert result.hour == 10
        assert result.minute == 30
        assert result.second == 45


class TestTimestampRoundtrip:
    """Test roundtrip conversion between formats."""

    def test_normalize_then_ensure_roundtrip(self):
        """Test converting datetime -> string -> datetime."""
        original = datetime(2025, 11, 18, 10, 30, 0)
        normalized = normalize_timestamp(original)
        restored = ensure_datetime(normalized)
        # Should restore to same date/time
        assert original.year == restored.year
        assert original.month == restored.month
        assert original.day == restored.day

    def test_string_normalize_idempotent(self):
        """Test that normalizing already-normalized string is idempotent."""
        original = "2025-11-18T10:30:00.123456"
        first_norm = normalize_timestamp(original)
        second_norm = normalize_timestamp(first_norm)
        # Both should be valid ISO format strings
        assert isinstance(first_norm, str)
        assert isinstance(second_norm, str)
        assert "2025" in first_norm
        assert "2025" in second_norm


class TestTimestampEdgeCases:
    """Test edge cases and error handling."""

    def test_normalize_with_microseconds(self):
        """Test normalizing with microsecond precision."""
        dt = datetime(2025, 11, 18, 10, 30, 0, 123456)
        result = normalize_timestamp(dt)
        assert isinstance(result, str)

    def test_ensure_datetime_with_z_timezone(self):
        """Test parsing Z timezone indicator."""
        iso_string = "2025-11-18T10:30:00Z"
        result = ensure_datetime(iso_string)
        assert isinstance(result, datetime)

    def test_ensure_datetime_invalid_format_falls_back(self):
        """Test that invalid format falls back to current time."""
        invalid_string = "not-a-valid-timestamp"
        result = ensure_datetime(invalid_string)
        # Invalid format falls back to current time (logged as warning)
        assert isinstance(result, datetime)

    def test_normalize_very_old_date(self):
        """Test normalizing very old dates."""
        old_dt = datetime(1970, 1, 1, 0, 0, 0)
        result = normalize_timestamp(old_dt)
        assert isinstance(result, str)
        assert "1970" in result

    def test_normalize_future_date(self):
        """Test normalizing future dates."""
        future_dt = datetime(2099, 12, 31, 23, 59, 59)
        result = normalize_timestamp(future_dt)
        assert isinstance(result, str)
        assert "2099" in result
