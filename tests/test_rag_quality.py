"""Quality of the full RAG pipeline, judged by an LLM through DeepEval.

Needs the database, the BGE-M3 model and the API. For each question: Haiku calls of the pipeline
plus several judge calls per metric (judge model: env var JUDGE_MODEL, Haiku by default).
Each run writes its reports in tests/reports/rag_quality/<timestamp>/ (see conftest.py for the summary).
"""
import json

import pytest
from deepeval.metrics import AnswerRelevancyMetric, FaithfulnessMetric, GEval
from deepeval.test_case import LLMTestCase, SingleTurnParams

from api.dates import WEEKDAYS, describe_periods
from api.llm import format_event
from api.rag import answer
from tests.helpers import QUESTION_IDS, QUESTIONS, RUN_DIR, TODAY
from tests.judge import ClaudeJudge, estimate_cost

pytestmark = pytest.mark.llm

CONSTRAINTS_CRITERIA = """The user asks for events matching some constraints: a place, a type of event and a period (today's date is given at the start of the input). The retrieval context holds the candidate events found in the database.
Determine whether the actual output respects these rules:
- every event it presents as a recommendation must, according to the retrieval context, match the requested place (same city or a very close one), the requested type of event and take place in the requested period (dates and, if asked, time of day);
- if no candidate in the retrieval context matches, the output must say so clearly first. It may then suggest up to 3 close alternatives (for example the requested type of event in a nearby town, or a similar type of event in the requested place), provided they are in a separate part of the answer and clearly presented as not matching, saying what differs. Such alternatives are not a fault and must not lower the score;
- the output must not present non-matching events as matches, suggest alternatives when matching events exist, suggest more than 3 alternatives, or suggest alternatives far from the request.
Recommending few events is fine."""


@pytest.fixture(scope="module")
def judge():
    return ClaudeJudge()


@pytest.mark.parametrize("question", QUESTIONS, ids=QUESTION_IDS)
def test_rag_answer_quality(question, embedding_model, judge):
    result = answer(question["query"], embedding_model, today=TODAY)

    retrieval_context = [format_event(i + 1, event, timings) for i, (event, timings) in enumerate(result.events)]
    test_case = LLMTestCase(
        input=f"(Today is {WEEKDAYS[TODAY.weekday()]} {TODAY.isoformat()}) {question['query']}",
        actual_output=result.answer,
        retrieval_context=retrieval_context or ["(no event found for this period)"],
    )

    metrics = [
        # Every claim of the answer must be supported by the retrieved events (no invented event or detail)
        FaithfulnessMetric(threshold=0.8, model=judge),
        GEval(
            name="Constraints respected",
            criteria=CONSTRAINTS_CRITERIA,
            evaluation_params=[SingleTurnParams.INPUT, SingleTurnParams.ACTUAL_OUTPUT, SingleTurnParams.RETRIEVAL_CONTEXT],
            threshold=0.7,
            model=judge,
        ),
    ]
    if not question.get("no_answer_expected"):
        # An honest "nothing found" would be scored as irrelevant, so only for questions that have answers
        metrics.append(AnswerRelevancyMetric(threshold=0.7, model=judge))

    usage_before = dict(judge.usage)
    scores = {}
    for metric in metrics:
        metric.measure(test_case, _show_indicator=False)
        scores[metric.__name__] = {
            "score": metric.score,
            "threshold": metric.threshold,
            "success": metric.is_successful(),
            "reason": metric.reason,
        }

    judge_usage = {key: judge.usage[key] - usage_before[key] for key in judge.usage}
    judge_usage["cost_usd"] = estimate_cost(judge.get_model_name(), judge_usage)

    RUN_DIR.mkdir(parents=True, exist_ok=True)
    (RUN_DIR / f"{question['id']}.json").write_text(json.dumps({
        "query": question["query"],
        "periods": describe_periods(result.periods),
        "retrieved": [event.title_fr for event, _ in result.events],
        "answer": result.answer,
        "scores": scores,
        "judge_model": judge.get_model_name(),
        "judge_usage": judge_usage,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    failed = [name for name, s in scores.items() if not s["success"]]
    assert not failed, "\n".join(f"{name}: {scores[name]['score']:.2f} < {scores[name]['threshold']} - {scores[name]['reason']}" for name in failed)
