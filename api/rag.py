import datetime
import sys

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from api.dates import describe_periods, overlaps, to_intervals
from api.llm import extract_periods, generate_answer
from api.retrieval import retrieve
from database import Session
from models import Event


def load_events(event_uids, intervals):
    """Load the events in relevance order, each with its timings overlapping the intervals (sorted by begin)."""
    with Session() as session:
        events = session.execute(
            select(Event).where(Event.uid.in_(event_uids)).options(selectinload(Event.timings))
        ).scalars().all()
        by_uid = {event.uid: event for event in events}
        result = []
        for uid in event_uids:
            event = by_uid.get(uid)
            if event is None:
                continue
            timings = sorted(
                (t for t in event.timings if overlaps(t.begin, t.end, intervals)),
                key=lambda t: t.begin,
            )
            result.append((event, timings))
        session.expunge_all()
    return result


def answer(query, embedding_model, top_k=30, today=None):
    today = today or datetime.date.today()
    periods = extract_periods(query, today=today)
    intervals = to_intervals(periods)
    results = retrieve(query, embedding_model, top_k=top_k, intervals=intervals)
    events = load_events([uid for uid, *_ in results], intervals)
    return generate_answer(query, events, periods, today=today), periods, results


if __name__ == "__main__":
    from FlagEmbedding import BGEM3FlagModel

    query = " ".join(sys.argv[1:]) or "Un concert de musique classique à Paris"
    model = BGEM3FlagModel("BAAI/bge-m3", use_fp16=False, devices="cpu")
    response, periods, results = answer(query, model)
    print(f"Query: {query}")
    print(f"Periods: {describe_periods(periods)}")
    print(f"Retrieved events: {[uid for uid, *_ in results]}\n")
    print(response)
