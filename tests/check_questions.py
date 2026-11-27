"""For each test question, list the events in the DB matching city + expected period + a type regex.
Here to help manual checks of whether events actually exist for a given question."""
import sys

from sqlalchemy import bindparam, exists, func, literal, select
from sqlalchemy.dialects.postgresql import TSMULTIRANGE, Range

from api.dates import to_intervals
from database import Session
from models import Event, Timing
from tests.helpers import QUESTIONS, expected_periods

# question id -> (city or None, type regex or None)
CHECKS = {
    "no_date": ("Bordeaux", None),
    "weekend": ("Nantes", None),
    "tonight": ("Paris", r"th[eé][aâ]tre|pi[eè]ce|com[eé]die"),
    "weekday_afternoon": ("Rennes", r"atelier"),
    "next_week": ("Toulouse", r"expo"),
    "explicit_date": ("Bordeaux", r"march[eé] de no[eë]l"),
    "tomorrow_morning": ("Rouen", None),
    "every_saturday": ("Roubaix", r"visite guid[eé]e"),
    "several_days": ("Nantes", r"sang"),
    "two_slots": ("Nantes", r"concert"),
    "month": ("Meudon", r"op[eé]ra"),
    "after_hour": ("Toulouse", None),
    "past_month": ("Lille", r"concert"),
    "rare_type": ("Nantes", r"yoga|m[eé]ditation"),
    "christmas_day": ("Toulouse", None),
    "no_answer_tonight": ("Draguignan", r"curling"),
    "no_answer_date": ("Al[eè]s", r"forge"),
}

only = sys.argv[1:]
for q in QUESTIONS:
    if only and q["id"] not in only:
        continue
    city, pattern = CHECKS[q["id"]]
    intervals = to_intervals(expected_periods(q))
    periods = bindparam("periods", value=[Range(s, e, bounds="[)") for s, e in intervals], type_=TSMULTIRANGE)
    in_period = exists().where(
        Timing.event_uid == Event.uid,
        func.tsrange(Timing.begin, Timing.end, literal("[]")).op("&&")(periods),
    )
    stmt = select(Event.uid, Event.title_fr, Event.location_city).where(in_period)
    if city:
        stmt = stmt.where(Event.location_city.op("~*")(f"^{city}$"))
    if pattern:
        text = func.concat_ws(" ", Event.title_fr, Event.description_fr, Event.longdescription_fr, Event.keywords_fr)
        stmt = stmt.where(text.op("~*")(pattern))
    with Session.begin() as session:
        rows = session.execute(stmt.order_by(Event.title_fr)).all()
    titles = sorted({r.title_fr for r in rows})
    events = [(r.uid, r.title_fr) for r in rows]
    print(f"\n### {q['id']} — {q['query']}  [{city} / {pattern}] -> {len(rows)} events, {len(titles)} distinct titles")
    #for t in titles[:25]:
    #    print("   -", t[:110])
    for uid, title in events[:25]:
        print(f"   - {uid} — {title[:110]}")
