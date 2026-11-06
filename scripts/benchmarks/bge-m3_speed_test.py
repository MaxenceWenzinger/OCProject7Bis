import time

import ollama
from FlagEmbedding import BGEM3FlagModel
from sqlalchemy import func

from database import Session
from models import Event

if __name__ == "__main__":
    TEST_SIZE = 1000
    BATCH_SIZE = 16
    with Session.begin() as session:
        random_events = session.query(Event).order_by(func.random()).limit(TEST_SIZE).all()
        texts = [f"{event.title_fr}\n{event.description_fr}" for event in random_events]


    ollama.embed(model="bge-m3:latest", input="warm-up", options={"num_ctx": 8192, "num_gpu": 0})

    start = time.perf_counter()
    for i in range(0, len(texts), BATCH_SIZE):
        response = ollama.embed(
            model="bge-m3:latest",
            input=texts[i:i + BATCH_SIZE],
            options={"num_ctx": 8192, "num_gpu": 0},
        )
    elapsed = time.perf_counter() - start
    print(f"Embedding {len(texts)} texts took {elapsed:.2f} seconds, or {elapsed / len(texts):.4f} seconds per text.")

    

    model = BGEM3FlagModel("BAAI/bge-m3", use_fp16=False, devices="cpu")

    start = time.perf_counter()
    out = model.encode(
        texts,
        batch_size=BATCH_SIZE,
        max_length=8192,
        return_dense=True,
        return_sparse=True,
        return_colbert_vecs=False,
    )
    elapsed = time.perf_counter() - start
    print(f"Encoding {len(texts)} texts took {elapsed:.2f} seconds, or {elapsed / len(texts):.4f} seconds per text.")
    dense = out["dense_vecs"]
    sparse = out["lexical_weights"]
