"""Unit tests for parsing cloud day/time strings, including '24:00' end of day."""

from datetime import datetime

from anker_solix_api.energy import _day_time_to_datetime

DAY = datetime(2026, 11, 3)


def test_regular_time_seconds() -> None:
    assert _day_time_to_datetime(DAY, "13:05:00", "%H:%M:%S") == datetime(2026, 11, 3, 13, 5)


def test_regular_time_minutes() -> None:
    assert _day_time_to_datetime(DAY, "23:55", "%H:%M") == datetime(2026, 11, 3, 23, 55)


def test_end_of_day_seconds() -> None:
    assert _day_time_to_datetime(DAY, "24:00:00", "%H:%M:%S") == datetime(2026, 11, 4)


def test_end_of_day_minutes_month_rollover() -> None:
    assert _day_time_to_datetime(datetime(2026, 11, 30), "24:00", "%H:%M") == datetime(2026, 12, 1)
