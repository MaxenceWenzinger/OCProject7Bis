from pgvector import SparseVector
from sqlalchemy import select

from database import Session
from models import Vector


def retrieve(query, model, dense_weight = 1.0, sparse_weight = 1.0, top_k = 10):
    out = model.encode(
        [query],
        max_length=8192,
        return_dense=True,
        return_sparse=True,
        return_colbert_vecs=False)
    dense = out["dense_vecs"][0]
    sparse = out["lexical_weights"][0]
    sparse=SparseVector({int(k): float(v) for k, v in sparse.items()}, 250002)
    dense_score = -Vector.vector.max_inner_product(dense)
    sparse_score = -Vector.sparse.max_inner_product(sparse)
    score = dense_weight * dense_score + sparse_weight * sparse_score
    stmt = select(Vector.event_uid,
                  dense_score.label("dense_score"),
                  sparse_score.label("sparse_score"),
                  score.label("score")).order_by(score.desc()).limit(top_k)
    with Session.begin() as session:
        rows = session.execute(stmt).all()
    return [(row.event_uid, row.dense_score, row.sparse_score, row.score) for row in rows]

if __name__ == "__main__":
    from scripts.vectorize import BGEM3FlagModel
    model = BGEM3FlagModel("BAAI/bge-m3", use_fp16=False, devices="cpu")
    query = "Concert de musique classique à Paris"
    results = retrieve(query, model)
    print(results)