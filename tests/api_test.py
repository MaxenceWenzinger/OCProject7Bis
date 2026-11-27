"""Functional tests of the REST API (api/app.py).

The embedding model, the RAG pipeline and the vectorization are replaced by fakes,
so these tests need neither the database, nor BGE-M3, nor the Anthropic API.
"""
import datetime
import types

import pytest
from fastapi.testclient import TestClient

import api.app as app_module
from api.dates import Period
from api.rag import RagResult
from config import settings


def fake_event(uid, title, city):
    return types.SimpleNamespace(uid=uid, title_fr=title, location_city=city,
                                 canonicalurl=f"https://openagenda.com/e/{uid}")


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(app_module, "load_embedding_model", lambda: "fake-model")
    monkeypatch.setattr(settings, "admin_token", None)
    with TestClient(app_module.app) as client:
        yield client


@pytest.fixture
def fake_answer(monkeypatch):
    calls = []

    def answer(query, embedding_model, **kwargs):
        calls.append((query, embedding_model))
        period = Period(datetime.date(2026, 11, 28), datetime.date(2026, 11, 29))
        return RagResult(
            answer="Je vous recommande le concert X.",
            periods=[period],
            results=[(1, 0.5, 0.1, 0.6), (2, 0.4, 0.1, 0.5)],
            events=[(fake_event(1, "Concert X", "Lyon"), []), (fake_event(2, "Concert Y", "Villeurbanne"), [])],
        )

    monkeypatch.setattr(app_module.rag, "answer", answer)
    return calls


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ask_returns_the_answer_and_the_events(client, fake_answer):
    response = client.post("/ask", json={"question": "  Un concert de jazz à Lyon ce week-end  "})
    assert response.status_code == 200
    body = response.json()
    assert body["question"] == "Un concert de jazz à Lyon ce week-end"
    assert body["answer"] == "Je vous recommande le concert X."
    assert body["periods"]
    assert [e["uid"] for e in body["events"]] == [1, 2]
    assert body["events"][0] == {"uid": 1, "title": "Concert X", "city": "Lyon",
                                 "url": "https://openagenda.com/e/1", "score": 0.6}
    # The question is stripped, and the model loaded at startup is reused
    assert fake_answer == [("Un concert de jazz à Lyon ce week-end", "fake-model")]


@pytest.mark.parametrize("payload", [{"question": ""}, {"question": "   "}, {}, {"question": 42}, {"q": "jazz"}])
def test_ask_rejects_invalid_questions(client, fake_answer, payload):
    response = client.post("/ask", json=payload)
    assert response.status_code == 422
    assert fake_answer == []


def test_ask_rejects_non_json_body(client, fake_answer):
    response = client.post("/ask", content="not json", headers={"Content-Type": "application/json"})
    assert response.status_code == 422


def test_ask_get_not_allowed(client):
    assert client.get("/ask").status_code == 405


def test_ask_database_error_returns_503(client, monkeypatch):
    from sqlalchemy.exc import OperationalError

    def answer(*args, **kwargs):
        raise OperationalError("SELECT 1", {}, Exception("connection refused"))

    monkeypatch.setattr(app_module.rag, "answer", answer)
    response = client.post("/ask", json={"question": "jazz"})
    assert response.status_code == 503


def test_rebuild_runs_vectorize(client, monkeypatch):
    calls = []
    monkeypatch.setattr(app_module, "run_vectorize", lambda model, reset: calls.append((model, reset)))

    response = client.post("/rebuild")
    assert response.status_code == 202
    assert response.json()["running"] is True
    # TestClient runs the background task before returning
    assert calls == [("fake-model", False)]
    status = client.get("/rebuild").json()
    assert status["running"] is False and status["error"] is None and status["finished_at"]

    assert client.post("/rebuild", json={"reset": True}).status_code == 202
    assert calls[-1] == ("fake-model", True)


def test_rebuild_reports_errors(client, monkeypatch):
    def fail(model, reset):
        raise RuntimeError("boom")

    monkeypatch.setattr(app_module, "run_vectorize", fail)
    assert client.post("/rebuild").status_code == 202
    status = client.get("/rebuild").json()
    assert status["running"] is False
    assert status["error"] == "RuntimeError: boom"


def test_rebuild_refuses_concurrent_runs(client):
    state = client.app.state.rebuild
    assert state.try_start(reset=False)
    assert client.post("/rebuild").status_code == 409
    state.finish()


def test_rebuild_requires_token_when_configured(client, monkeypatch):
    monkeypatch.setattr(app_module, "run_vectorize", lambda model, reset: None)
    monkeypatch.setattr(settings, "admin_token", "secret")
    assert client.post("/rebuild").status_code == 401
    assert client.post("/rebuild", headers={"X-Admin-Token": "wrong"}).status_code == 401
    assert client.post("/rebuild", headers={"X-Admin-Token": "secret"}).status_code == 202


@pytest.mark.db
@pytest.mark.llm
def test_ask_end_to_end():
    """Real pipeline: BGE-M3, the database and the Anthropic API."""
    with TestClient(app_module.app) as client:
        response = client.post("/ask", json={"question": "Un concert de musique classique à Paris"})
    assert response.status_code == 200
    body = response.json()
    assert body["answer"].strip()
    assert body["events"]
