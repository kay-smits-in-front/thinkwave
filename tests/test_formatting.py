from datetime import UTC, datetime, timedelta

import pytest

from app.formatting import action_duration, as_utc, format_duration, mask_email


@pytest.mark.parametrize(
    ("days", "text"),
    [(0, "minder dan 1 dag"), (1, "1 dag"), (6, "6 dagen"), (14, "2 weken"), (45, "6 weken"), (90, "3 maanden")],
)
def test_format_duration(days, text):
    assert format_duration(timedelta(days=days)) == text


def test_duration_runs_to_now_while_action_is_active():
    start = datetime(2026, 1, 1, tzinfo=UTC)
    now = datetime(2026, 1, 11, tzinfo=UTC)
    assert action_duration(start, None, now) == timedelta(days=10)


def test_duration_stops_at_completion():
    start = datetime(2026, 1, 1, tzinfo=UTC)
    done = datetime(2026, 1, 8, tzinfo=UTC)
    assert action_duration(start, done, datetime(2026, 6, 1, tzinfo=UTC)) == timedelta(days=7)


def test_naive_datetimes_from_sqlite_are_treated_as_utc():
    assert as_utc(datetime(2026, 1, 1)).tzinfo is UTC


def test_mask_email_hides_most_of_the_address():
    assert mask_email("jan@acme.nl") == "j***@acme.nl"
