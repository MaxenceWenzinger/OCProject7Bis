import json
import os

# Must be set before deepeval is imported anywhere
os.environ.setdefault("DEEPEVAL_TELEMETRY_OPT_OUT", "YES")

import pytest

from config import settings
from tests.helpers import QUESTIONS, RUN_DIR, RUN_ID, SUMMARY_NAME, TODAY


@pytest.fixture(scope="session")
def embedding_model():
    from FlagEmbedding import BGEM3FlagModel
    return BGEM3FlagModel("BAAI/bge-m3", use_fp16=False, devices="cpu")


def _short(metric_name):
    return metric_name.split(" [")[0]


def _load_reports():
    reports = {}
    for path in sorted(RUN_DIR.glob("*.json")):
        if path.stem != SUMMARY_NAME:
            reports[path.stem] = json.loads(path.read_text(encoding="utf-8"))
    return reports


def _build_summary(reports):
    metric_names = list(dict.fromkeys(_short(name) for r in reports.values() for name in r["scores"]))
    averages = {}
    for metric in metric_names:
        values = [s["score"] for r in reports.values() for name, s in r["scores"].items() if _short(name) == metric]
        averages[metric] = sum(values) / len(values)
    usage = {"calls": 0, "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0}
    for r in reports.values():
        for key, value in usage.items():
            if value is not None:
                usage[key] = None if r["judge_usage"][key] is None else usage[key] + r["judge_usage"][key]
    return {
        "run_id": RUN_ID,
        "reference_date": TODAY.isoformat(),
        "pipeline_model": settings.llm_model,
        "judge_model": sorted({r["judge_model"] for r in reports.values()}),
        "questions_evaluated": len(reports),
        "questions_total": len(QUESTIONS),
        "passed": sum(all(s["success"] for s in r["scores"].values()) for r in reports.values()),
        "averages": averages,
        "judge_usage": usage,
        "questions": {
            qid: {_short(name): {"score": s["score"], "success": s["success"]} for name, s in r["scores"].items()}
            for qid, r in reports.items()
        },
    }, metric_names


def _summary_markdown(summary, metric_names):
    usage = summary["judge_usage"]
    cost = "unknown (model not in PRICES)" if usage["cost_usd"] is None else f"${usage['cost_usd']:.2f}"
    lines = [
        f"# RAG quality run {summary['run_id']}",
        "",
        f"- Reference date: {summary['reference_date']}",
        f"- Pipeline model: {summary['pipeline_model']}",
        f"- Judge model: {', '.join(summary['judge_model'])}",
        f"- Questions evaluated: {summary['questions_evaluated']}/{summary['questions_total']}, passed: {summary['passed']}",
        f"- Judge usage: {usage['calls']} calls, {usage['input_tokens']:,} input tokens, {usage['output_tokens']:,} output tokens, estimated cost {cost}",
        "",
        "| Question | " + " | ".join(metric_names) + " | Result |",
        "|---" * (len(metric_names) + 2) + "|",
    ]
    for qid, scores in summary["questions"].items():
        cells = []
        for metric in metric_names:
            s = scores.get(metric)
            cells.append("–" if s is None else f"{s['score']:.2f}" if s["success"] else f"**{s['score']:.2f}**")
        result = "pass" if all(s["success"] for s in scores.values()) else "**fail**"
        lines.append(f"| {qid} | " + " | ".join(cells) + f" | {result} |")
    lines += ["", "Averages: " + ", ".join(f"{m} {v:.2f}" for m, v in summary["averages"].items()), ""]
    return "\n".join(lines)


def pytest_terminal_summary(terminalreporter, config):
    """After a RAG quality run, write the summary of the run and print the scores."""
    if hasattr(config, "workerinput") or not RUN_DIR.exists():
        return  # xdist worker, or no RAG quality test ran
    reports = _load_reports()
    if not reports:
        return
    summary, metric_names = _build_summary(reports)
    (RUN_DIR / f"{SUMMARY_NAME}.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (RUN_DIR / f"{SUMMARY_NAME}.md").write_text(_summary_markdown(summary, metric_names), encoding="utf-8")

    terminalreporter.section("RAG quality scores")
    for qid, scores in summary["questions"].items():
        cells = "  ".join(f"{name}: {s['score']:.2f}{'' if s['success'] else ' FAIL'}" for name, s in scores.items())
        terminalreporter.write_line(f"{qid:<20} {cells}")
    usage = summary["judge_usage"]
    cost = "unknown" if usage["cost_usd"] is None else f"${usage['cost_usd']:.2f}"
    terminalreporter.write_line(
        f"Passed {summary['passed']}/{summary['questions_evaluated']}. "
        f"Judge ({', '.join(summary['judge_model'])}): {usage['calls']} calls, estimated cost {cost}"
    )
    terminalreporter.write_line(f"Full answers, judge reasons and summary: {RUN_DIR}")
