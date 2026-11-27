"""Checks the periods extracted by the LLM against the expected ones (calls the API: ~20 Haiku requests)."""
import datetime as dt

import pytest

from api.dates import describe_periods, to_intervals
from api.llm import extract_periods
from tests.helpers import (
    QUESTION_IDS,
    QUESTIONS,
    TODAY,
    clip_intervals,
    expected_periods,
)

pytestmark = pytest.mark.llm


@pytest.mark.parametrize("question", QUESTIONS, ids=QUESTION_IDS)
def test_extracted_periods(question):
    expected = expected_periods(question)
    actual = extract_periods(question["query"], today=TODAY)

    # Compare the concrete intervals rather than the periods themselves:
    # "Tue, Fri, Sun" as one period with weekdays or as three single days are equivalent.
    expected_intervals = to_intervals(expected)
    actual_intervals = to_intervals(actual)
    if "check_until" in question:
        until = dt.date.fromisoformat(question["check_until"])
        expected_intervals = clip_intervals(expected_intervals, until)
        actual_intervals = clip_intervals(actual_intervals, until)

    assert actual_intervals == expected_intervals, (
        f"\nquery:    {question['query']}"
        f"\nexpected: {describe_periods(expected)}"
        f"\nactual:   {describe_periods(actual)}"
    )
