import datetime
import json
import os
import pathlib

from api.dates import Period, PeriodSchema

DATA = json.loads((pathlib.Path(__file__).parent / "data" / "questions.json").read_text(encoding="utf-8"))
TODAY = datetime.date.fromisoformat(DATA["today"])
QUESTIONS = DATA["questions"]
QUESTION_IDS = [q["id"] for q in QUESTIONS]

REPORTS_ROOT = pathlib.Path(__file__).parent / "reports" / "rag_quality"
# One folder per run. The main pytest process sets the variable first and the xdist workers inherit it,
# so they all write into the same folder.
RUN_ID = os.environ.setdefault("RAG_QUALITY_RUN_ID", datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))
RUN_DIR = REPORTS_ROOT / RUN_ID
SUMMARY_NAME = "summary"


def expected_periods(question):
    return [Period.from_schema(PeriodSchema(**p)) for p in question["expected_periods"]]


def clip_intervals(intervals, until):
    """Keep only the part of the intervals before the end of day `until` (a date)."""
    limit = datetime.datetime.combine(until + datetime.timedelta(days=1), datetime.time.min)
    return [(start, min(end, limit)) for start, end in intervals if start < limit]
