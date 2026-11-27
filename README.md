## Dataset download
'''
uv run -m scripts.download_data
'''
The data gets saved in data/raw/

## Dataset filtering
'''
uv run -m scripts.filter_data
'''
The filtered data gets saved in data/filtered/

## Storing the data in PostgreSQL
Create your database.  
Make a .env.  
Install pgvector:  
https://github.com/pgvector/pgvector#installation-notes---windows  
'''
uv run alembic upgrade head
uv run -m scripts.populate_db
'''

## Asking a question
Add your Anthropic API key to the .env (`ANTHROPIC_API_KEY=...`). The model can be changed with `LLM_MODEL` (default: `claude-haiku-5-5`).
'''
uv run -m api.rag "Un concert de jazz à Lyon ce week-end"
'''
The pipeline asks the LLM for the period the user is interested in, retrieves the n most relevant events with at least one date in that period, and has the LLM write the answer from them.

## Tests
Unit tests (no API call):
'''
uv run pytest
'''
Retrieval tests (no API call, but needs a local bge-m3):
'''
uv run pytest -m db
'''
Tests calling the Anthropic API (they cost credits), on the questions of tests/data/questions.json:
'''
uv run pytest -m llm tests/test_date_extraction.py
uv run pytest -m llm tests/test_rag_quality.py -n 4
'''
The RAG quality tests use DeepEval with Claude as the judge (faithfulness, answer relevancy, and a custom criterion checking that the recommended events match the requested place, type and period). The judge is Claude Haiku 5.5 by default; set the `JUDGE_MODEL` environment variable (or put it in .env) to use another model, e.g. `claude-sonnet-5-5`. Each run is saved in tests/reports/rag_quality/<timestamp>/: one JSON per question (answer, retrieved events, scores, judge reasons, judge tokens and estimated cost) plus summary.md and summary.json for the whole run.
