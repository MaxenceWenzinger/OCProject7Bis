from pgvector import SparseVector

from database import Session
from models import Event, Vector


def build_header(event):
    mots_clefs = f"\n{event.keywords_fr}" if event.keywords_fr else ""

    address = f", {event.location_address}" if event.location_address else ""
    city = f", {event.location_city}" if event.location_city else ""
    department = f", {event.location_department}" if event.location_department else ""
    region = f", {event.location_region}" if event.location_region else ""
    lieu = f"\n{event.location_name}{address}{city}{department}{region}"
    return f"{event.title_fr}{mots_clefs}{lieu}"

def build_content(event):
    CHUNK_SIZE = 1600
    COMMON_SLICE = 320
    longdescription = f"\n{event.longdescription_fr}" if event.longdescription_fr else ""
    content = f"{event.description_fr}{longdescription}"
    result = []
    start = 0
    end = 0
    while start + CHUNK_SIZE < len(content):
        for char in [".", "\n", "?", ",", "!", ";", ":", ")", "]", "}"]:
            end = max(end, content.rfind(char, start + COMMON_SLICE * 2, start + CHUNK_SIZE) + 1)
        if end < start + COMMON_SLICE * 2:
            end = start + CHUNK_SIZE
        result.append(content[start:end].strip())
        start = end
        for char in [".", "\n", "?", ",", "!", ";", ":", ")", "]", "}"]:
            pos = content.find(char, end - COMMON_SLICE, end)
            if pos != -1:
                start = min(start, pos + 1)
    result.append(content[start:].strip())
    return result

def vectorize(model, reset=False):
    """Embed the events and store their vectors.

    The run is resumable: it starts again from the last vectorized event (re-embedding it,
    in case it was interrupted) and embeds all the events after it.
    reset=True deletes all the vectors first, to rebuild everything from scratch.
    """
    BATCH_SIZE = 16
    EVENTS_PER_RUN = 1000
    if reset:
        with Session.begin() as session:
            session.query(Vector).delete()
    not_finished = True
    while not_finished:
        with Session.begin() as session:
            # We need to delete the last vector in case the last run was interrupted, to avoid having a partial embedding for an event
            highest_vector = session.query(Vector).order_by(Vector.event_uid.desc()).first()
            highest_uid = highest_vector.event_uid if highest_vector else 0
            session.query(Vector).filter(Vector.event_uid == highest_uid).delete()

            events = session.query(Event).filter(Event.uid >= highest_uid).order_by(Event.uid).limit(EVENTS_PER_RUN).all()
            not_finished = len(events) == EVENTS_PER_RUN
            headers = [build_header(event) for event in events]
            contents = [build_content(event) for event in events]
            uids = [event.uid for event in events]
        documents = [f"{header}\n{content}" for header, content_list in zip(headers, contents) for content in content_list]
        document_uids = [uid for uid, content_list in zip(uids, contents) for _ in content_list]

        out = model.encode(
            documents,
            batch_size=BATCH_SIZE,
            max_length=8192,
            return_dense=True,
            return_sparse=True,
            return_colbert_vecs=False,
        )
        dense = out["dense_vecs"]
        sparse = out["lexical_weights"]

        with Session.begin() as session:
            for i, uid in enumerate(document_uids):
                vector_entry = Vector(
                    event_uid=uid,
                    vector=dense[i],
                    sparse=SparseVector({int(k): float(v) for k, v in sparse[i].items()}, 250002)
                )
                session.add(vector_entry)


if __name__ == "__main__":
    import sys

    from FlagEmbedding import BGEM3FlagModel
    model = BGEM3FlagModel("BAAI/bge-m3", use_fp16=False, devices="cpu")
    vectorize(model, reset="--reset" in sys.argv[1:])
