"""Checks that the retrieval finds the expected events (needs the database and the BGE-M3 model, no API call).

The search is filtered with the expected periods rather than the ones extracted by the LLM,
so a failure here points to the retrieval itself, not to the date extraction (see test_date_extraction.py).
"""
import pytest

from api.dates import to_intervals
from api.retrieval import retrieve
from tests.helpers import QUESTION_IDS, QUESTIONS, expected_periods

pytestmark = pytest.mark.db


@pytest.mark.parametrize("question", QUESTIONS, ids=QUESTION_IDS)
def test_expected_events_are_retrieved(question, embedding_model):
    expected_uids = question.get("expected_uids", [])
    if not expected_uids:
        pytest.skip("no expected_uids for this question")

    intervals = to_intervals(expected_periods(question))
    retrieved = [uid for uid, *_ in retrieve(question["query"], embedding_model, intervals=intervals)]

    missing = [uid for uid in expected_uids if uid not in retrieved]
    assert not missing, (
        f"\nquery:     {question['query']}"
        f"\nmissing:   {missing}"
        f"\nretrieved: {retrieved}"
    )
