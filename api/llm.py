import datetime

import anthropic

from api.dates import (
    DEFAULT_RANGE_DAYS,
    WEEKDAYS,
    DateFilterSchema,
    Period,
    default_periods,
    describe_periods,
)
from config import settings

client = anthropic.Anthropic(api_key=settings.anthropic_api_key)


DATE_EXTRACTION_SYSTEM = f"""You extract when a user wants to attend an event, from their request for cultural or public events (concerts, exhibitions, visits, workshops...). Requests are usually in French.

Return a list of periods. Each period has:
- start_date and end_date: inclusive, format YYYY-MM-DD.
- weekdays: ISO weekday numbers to keep inside the period (1 = Monday, ..., 7 = Sunday). Empty list = every day.
- start_time and end_time: time of day, format HH:MM, or null when the request gives no time of day. end_time may be earlier than start_time for a slot crossing midnight.
Use several periods only for disjoint dates or for different times of day on different days. Prefer one period with weekdays over many single-day periods.

Dates:
- Explicit dates or periods ("le 14 juillet", "en mars", "du 3 au 5 mai"): use them. A date without a year is the next occurrence of that date, today included, unless the sentence clearly refers to the past, in which case return the last occurrence of that date.
- Relative expressions: resolve them from today's date. "ce mardi" / "mardi" is the next Tuesday (today if today is Tuesday). "ce week-end" is the coming Saturday and Sunday (or the current one if today is Saturday or Sunday). "la semaine prochaine" is next Monday to next Sunday. "demain", "ce soir", "aujourd'hui" are single days.
- Several days ("mardi, vendredi ou dimanche"): one period covering the next occurrence of each day, with those weekdays.
- Recurring days ("tous les mercredis", "le dimanche", "les week-ends"): today to 90 days from today, with those weekdays, unless the request bounds it ("tous les mercredis de décembre").
- Recurrence describing the event itself rather than the user's availability ("tous les ans", "chaque année", "annuel", "régulier"): not a date constraint, use today to 365 days from today.
- Past periods ("le mois dernier", "l'été dernier", past tenses) are allowed: return them as asked.
- No time indication at all, or vague near-future wording ("bientôt", "prochainement", "en ce moment"): today to {DEFAULT_RANGE_DAYS} days from today.

Times of day (only when the request mentions one, otherwise null):
- "le matin": 06:00 to 12:00. "à midi", "le midi": 11:30 to 14:00. "l'après-midi": 12:00 to 18:00. "le soir", "en soirée", "ce soir": 18:00 to 23:59. "la nuit": 22:00 to 05:00.
- "après 20h": start_time 20:00, end_time null. "avant 10h": start_time null, end_time 10:00. "vers 15h": 14:00 to 16:00.

Examples (today is Friday 2026-11-20):
- "un concert ce soir" -> [2026-11-20 to 2026-11-20, every day, 18:00 to 23:59]
- "une expo tous les mercredis" -> [2026-11-20 to 2027-02-18, weekdays [3], no time]
- "mardi, vendredi ou dimanche après-midi" -> [2026-11-20 to 2026-11-29, weekdays [2, 5, 7], 12:00 to 18:00]
- "samedi matin ou dimanche soir" -> [2026-11-21 to 2026-11-21, 06:00 to 12:00] and [2026-11-22 to 2026-11-22, 18:00 to 23:59]
- "à Noël ou au Nouvel An" -> [2026-12-24 to 2026-12-25] and [2026-12-31 to 2027-01-01]"""


def extract_periods(query, today=None):
    """Ask the LLM when the user wants to attend. Returns a list of api.dates.Period."""
    today = today or datetime.date.today()
    response = client.messages.parse(
        model=settings.llm_model,
        max_tokens=2048,
        system=DATE_EXTRACTION_SYSTEM,
        output_config={"effort": "low"},
        messages=[{
            "role": "user",
            "content": f"Today is {WEEKDAYS[today.weekday()]} {today.isoformat()}.\n\nUser request: {query}",
        }],
        output_format=DateFilterSchema,
    )

    if response.stop_reason != "end_turn" or response.parsed_output is None:
        return default_periods(today)
    periods = []
    for schema in response.parsed_output.periods:
        try:
            periods.append(Period.from_schema(schema))
        except ValueError:
            continue  # skip a malformed period, keep the others
    return periods or default_periods(today)


ANSWER_SYSTEM = """You are an assistant that recommends public cultural events in France (data from OpenAgenda).

You receive a user request and a list of candidate events retrieved from a database, already filtered on the period the user is interested in. Answer the user's request using only these events.

- Answer in the language of the user's request (usually French).
- Recommend the events that actually match the request; ignore the ones that don't. Not every candidate has to be mentioned.
- For each recommended event, give its title, when it takes place, where, and a short description of why it fits. Include its link when there is one.
- Never invent events, dates, places or details that are not in the provided data.
- If no candidate matches the request, say so plainly and, if relevant, suggest how the user could rephrase or widen their search (other dates, nearby places...)."""

MAX_DESCRIPTION_CHARS = 1500
MAX_TIMINGS_SHOWN = 5


def _format_event(index, event, timings):
    place = ", ".join(p for p in [event.location_name, event.location_address, event.location_city,
                                  event.location_department, event.location_region] if p)
    description = event.description_fr or ""
    if event.longdescription_fr:
        description += "\n" + event.longdescription_fr
    if len(description) > MAX_DESCRIPTION_CHARS:
        description = description[:MAX_DESCRIPTION_CHARS] + "…"

    timing_lines = [f"  - {t.begin:%Y-%m-%d %H:%M} → {t.end:%Y-%m-%d %H:%M}" for t in timings[:MAX_TIMINGS_SHOWN]]
    if len(timings) > MAX_TIMINGS_SHOWN:
        timing_lines.append(f"  - ... and {len(timings) - MAX_TIMINGS_SHOWN} other dates in the period")

    lines = [f'<event index="{index}">', f"Title: {event.title_fr}"]
    if event.keywords_fr:
        lines.append(f"Keywords: {event.keywords_fr}")
    lines.append(f"Place: {place or 'unknown'}")
    lines.append("Dates in the requested period:")
    lines.extend(timing_lines or ["  - unknown"])
    if event.conditions_fr:
        lines.append(f"Conditions: {event.conditions_fr}")
    if event.age_min is not None or event.age_max is not None:
        lines.append(f"Ages: {event.age_min if event.age_min is not None else '?'} - {event.age_max if event.age_max is not None else '?'}")
    if event.canonicalurl:
        lines.append(f"Link: {event.canonicalurl}")
    lines.append(f"Description:\n{description}")
    lines.append("</event>")
    result = "\n".join(lines)
    #print(result)
    return result


def generate_answer(query, events_with_timings, periods, today=None):
    """events_with_timings: list of (Event, [Timing]) ordered by relevance. periods: list of api.dates.Period."""
    today = today or datetime.date.today()
    if events_with_timings:
        events_text = "\n\n".join(_format_event(i + 1, e, t) for i, (e, t) in enumerate(events_with_timings))
    else:
        return "Aucun événement correspondant à votre demande n'a été trouvé dans la période indiquée."

    response = client.messages.create(
        model=settings.llm_model,
        max_tokens=4096,
        system=ANSWER_SYSTEM,
        output_config={"effort": "low"},
        messages=[{
            "role": "user",
            "content": (
                f"Today is {WEEKDAYS[today.weekday()]} {today.isoformat()}. "
                f"Period(s) considered: {describe_periods(periods)}.\n\n"
                f"<candidate_events>\n{events_text}\n</candidate_events>\n\n"
                f"User request: {query}"
            ),
        }],
    )

    if response.stop_reason == "refusal":
        return "Désolé, je ne peux pas répondre à cette demande."
    return "".join(block.text for block in response.content if block.type == "text")
