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
