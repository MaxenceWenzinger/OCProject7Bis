import datetime

from pgvector import SparseVector
from sqlalchemy import bindparam, exists, func, literal, select
from sqlalchemy.dialects.postgresql import TSMULTIRANGE, Range

from api.dates import Period, to_intervals
from database import Session
from models import Timing, Vector


def retrieve(query, model, dense_weight=1.0, sparse_weight=1.0, top_k=30, intervals=None):
    """Return the top_k most relevant distinct events for the query.

    intervals: optional list of (start, end) datetime intervals, end excluded (see api.dates.to_intervals).
    When given, only events having at least one timing overlapping one of the intervals are kept.
    Filtering happens in SQL before the limit, so we always get top_k events
    (unless fewer events match the filter).
    """
    out = model.encode(
        [query],
        max_length=8192,
        return_dense=True,
        return_sparse=True,
        return_colbert_vecs=False)
    dense = out["dense_vecs"][0]
    sparse = out["lexical_weights"][0]
    sparse = SparseVector({int(k): float(v) for k, v in sparse.items()}, 250002)
    dense_score = -Vector.vector.max_inner_product(dense)
    sparse_score = -Vector.sparse.max_inner_product(sparse)
    score = dense_weight * dense_score + sparse_weight * sparse_score

    # Events are split into several chunks (one vector each): keep only the best chunk per event.
    best_chunks = (
        select(Vector.event_uid,
               dense_score.label("dense_score"),
               sparse_score.label("sparse_score"),
               score.label("score"))
        .distinct(Vector.event_uid)
        .order_by(Vector.event_uid, score.desc())
    )
    if intervals is not None:
        # All the intervals go in a single tsmultirange parameter: one condition whatever their number.
        # "&&" is true if the timing [begin, end] overlaps at least one of the [start, end) intervals.
        periods = bindparam(
            "periods",
            value=[Range(start, end, bounds="[)") for start, end in intervals],
            type_=TSMULTIRANGE,
        )
        timing_range = func.tsrange(Timing.begin, Timing.end, literal("[]"))
        best_chunks = best_chunks.where(
            exists().where(
                Timing.event_uid == Vector.event_uid,
                timing_range.op("&&")(periods),
            )
        )
    best_chunks = best_chunks.subquery()

    stmt = select(best_chunks).order_by(best_chunks.c.score.desc()).limit(top_k)
    #print(stmt)
    with Session.begin() as session:
        rows = session.execute(stmt).all()
    return [(row.event_uid, row.dense_score, row.sparse_score, row.score) for row in rows]

if __name__ == "__main__":
    from scripts.vectorize import BGEM3FlagModel
    model = BGEM3FlagModel("BAAI/bge-m3", use_fp16=False, devices="cpu")
    query = "Concert de musique classique à Paris"
    today = datetime.date.today()
    # Wednesday and Saturday evenings over the next 30 days
    period = Period(today, today + datetime.timedelta(days=30), frozenset({3, 6}),
                    datetime.time(18, 0), datetime.time(23, 59))
    results = retrieve(query, model, intervals=to_intervals([period]))
    print(results)
