"""Time periods a user is interested in, and their expansion into concrete datetime intervals.

The LLM describes the user's request as a list of Periods (a date range, optionally restricted
to some weekdays and to a time of day). Each period is then expanded in Python into concrete
[start, end) datetime intervals, which are used to filter the events' timings.
"""
import dataclasses
import datetime

from pydantic import BaseModel, Field

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
DEFAULT_RANGE_DAYS = 30
MAX_PERIOD_DAYS = 400


# ---- Schema the LLM fills (structured output) ----

class PeriodSchema(BaseModel):
    start_date: str = Field(description="First day of the period, inclusive, format YYYY-MM-DD")
    end_date: str = Field(description="Last day of the period, inclusive, format YYYY-MM-DD")
    weekdays: list[int] = Field(description="ISO weekdays to keep inside the period (1 = Monday ... 7 = Sunday). Empty list = every day")
    start_time: str | None = Field(description="Start of the time of day, format HH:MM, or null for the start of the day")
    end_time: str | None = Field(description="End of the time of day, format HH:MM, or null for the end of the day. May be earlier than start_time for a time slot crossing midnight")


class DateFilterSchema(BaseModel):
    periods: list[PeriodSchema]


# ---- Validated periods used by the code ----

@dataclasses.dataclass(frozen=True)
class Period:
    start_date: datetime.date
    end_date: datetime.date
    weekdays: frozenset[int] = frozenset()
    start_time: datetime.time | None = None
    end_time: datetime.time | None = None

    @classmethod
    def from_schema(cls, schema):
        """Raises ValueError if the LLM output is not usable."""
        start = datetime.date.fromisoformat(schema.start_date)
        end = datetime.date.fromisoformat(schema.end_date)
        if end < start:
            start, end = end, start
        # Avoid generating thousands of intervals on a silly answer
        end = min(end, start + datetime.timedelta(days=MAX_PERIOD_DAYS))
        weekdays = frozenset(d for d in schema.weekdays if 1 <= d <= 7)
        start_time = datetime.time.fromisoformat(schema.start_time) if schema.start_time else None
        end_time = datetime.time.fromisoformat(schema.end_time) if schema.end_time else None
        return cls(start, end, weekdays, start_time, end_time)

    def describe(self):
        text = f"{self.start_date.isoformat()} to {self.end_date.isoformat()}"
        if self.weekdays and len(self.weekdays) < 7:
            text += ", " + ", ".join(WEEKDAYS[d - 1] for d in sorted(self.weekdays)) + " only"
        if self.start_time or self.end_time:
            text += f", from {self.start_time or datetime.time.min:%H:%M} to {self.end_time or datetime.time.max:%H:%M}"
        return text


def default_periods(today):
    return [Period(today, today + datetime.timedelta(days=DEFAULT_RANGE_DAYS))]


def describe_periods(periods):
    return "; ".join(p.describe() for p in periods)


def to_intervals(periods):
    """Expand periods into a sorted list of non-overlapping [start, end) datetime intervals."""
    intervals = []
    one_day = datetime.timedelta(days=1)
    for period in periods:
        day = period.start_date
        while day <= period.end_date:
            if not period.weekdays or day.isoweekday() in period.weekdays:
                start = datetime.datetime.combine(day, period.start_time or datetime.time.min)
                if period.end_time is None:
                    end = datetime.datetime.combine(day + one_day, datetime.time.min)
                else:
                    end = datetime.datetime.combine(day, period.end_time)
                    if end <= start:  # time slot crossing midnight, e.g. 22:00 -> 04:00
                        end += one_day
                intervals.append((start, end))
            day += one_day

    # Merge overlapping or touching intervals (consecutive whole days become a single interval)
    intervals.sort()
    merged = []
    for start, end in intervals:
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def overlaps(begin, end, intervals):
    """Same rule as the SQL filter: the timing [begin, end] overlaps an interval [start, stop)."""
    return any(begin < stop and end >= start for start, stop in intervals)
