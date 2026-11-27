"""Unit tests of api.dates: no API call, no database."""
import datetime as dt

import pytest

from api.dates import MAX_PERIOD_DAYS, Period, PeriodSchema, overlaps, to_intervals
from tests.helpers import QUESTION_IDS, QUESTIONS, expected_periods

FRIDAY = dt.date(2026, 11, 20)


def schema(start, end, weekdays=(), start_time=None, end_time=None):
    return PeriodSchema(start_date=start, end_date=end, weekdays=list(weekdays), start_time=start_time, end_time=end_time)


def test_consecutive_days_merge_into_one_interval():
    intervals = to_intervals([Period(FRIDAY, FRIDAY + dt.timedelta(days=9))])
    assert intervals == [(dt.datetime(2026, 11, 20), dt.datetime(2026, 11, 30))]


def test_weekdays_keep_only_those_days():
    # Wednesdays (3) and Saturdays (6) between Fri 20/11 and Sun 29/11: Sat 21, Wed 25, Sat 28
    intervals = to_intervals([Period(FRIDAY, dt.date(2026, 11, 29), frozenset({3, 6}))])
    assert [start.date() for start, _ in intervals] == [dt.date(2026, 11, 21), dt.date(2026, 11, 25), dt.date(2026, 11, 28)]
    assert all(end - start == dt.timedelta(days=1) for start, end in intervals)


def test_time_of_day_on_each_day():
    intervals = to_intervals([Period(FRIDAY, dt.date(2026, 11, 21), frozenset(), dt.time(18), dt.time(23, 59))])
    assert intervals == [
        (dt.datetime(2026, 11, 20, 18), dt.datetime(2026, 11, 20, 23, 59)),
        (dt.datetime(2026, 11, 21, 18), dt.datetime(2026, 11, 21, 23, 59)),
    ]


def test_slot_crossing_midnight_ends_next_day():
    intervals = to_intervals([Period(FRIDAY, FRIDAY, frozenset(), dt.time(22), dt.time(5))])
    assert intervals == [(dt.datetime(2026, 11, 20, 22), dt.datetime(2026, 11, 21, 5))]


def test_open_ended_times():
    after_20h = to_intervals([Period(FRIDAY, FRIDAY, frozenset(), dt.time(20), None)])
    before_10h = to_intervals([Period(FRIDAY, FRIDAY, frozenset(), None, dt.time(10))])
    assert after_20h == [(dt.datetime(2026, 11, 20, 20), dt.datetime(2026, 11, 21))]
    assert before_10h == [(dt.datetime(2026, 11, 20), dt.datetime(2026, 11, 20, 10))]


def test_overlapping_periods_are_merged():
    periods = [Period(FRIDAY, dt.date(2026, 11, 22)), Period(dt.date(2026, 11, 22), dt.date(2026, 11, 24))]
    assert to_intervals(periods) == [(dt.datetime(2026, 11, 20), dt.datetime(2026, 11, 25))]


@pytest.mark.parametrize("begin, end, expected", [
    (dt.datetime(2026, 11, 20, 19), dt.datetime(2026, 11, 20, 21), True),   # inside
    (dt.datetime(2026, 11, 20, 17), dt.datetime(2026, 11, 20, 19), True),   # partly inside
    (dt.datetime(2026, 11, 20, 0), dt.datetime(2026, 11, 20, 23, 59), True),  # all-day event
    (dt.datetime(2026, 11, 20, 14), dt.datetime(2026, 11, 20, 17), False),  # before
    (dt.datetime(2026, 11, 20, 23, 59), dt.datetime(2026, 11, 21, 1), False),  # starts when the interval ends (excluded)
])
def test_overlaps(begin, end, expected):
    evening = [(dt.datetime(2026, 11, 20, 18), dt.datetime(2026, 11, 20, 23, 59))]
    assert overlaps(begin, end, evening) is expected


def test_from_schema_swaps_reversed_dates_and_drops_invalid_weekdays():
    period = Period.from_schema(schema("2026-11-30", "2026-11-20", weekdays=[0, 3, 8]))
    assert (period.start_date, period.end_date) == (dt.date(2026, 11, 20), dt.date(2026, 11, 30))
    assert period.weekdays == frozenset({3})


def test_from_schema_caps_long_periods():
    period = Period.from_schema(schema("2026-01-01", "2035-01-01"))
    assert period.end_date - period.start_date == dt.timedelta(days=MAX_PERIOD_DAYS)


@pytest.mark.parametrize("bad", [schema("2026-13-01", "2026-12-01"), schema("2026-11-20", "2026-11-20", start_time="25:00")])
def test_from_schema_rejects_invalid_values(bad):
    with pytest.raises(ValueError):
        Period.from_schema(bad)


@pytest.mark.parametrize("question", QUESTIONS, ids=QUESTION_IDS)
def test_dataset_expected_periods_are_valid(question):
    assert to_intervals(expected_periods(question))
