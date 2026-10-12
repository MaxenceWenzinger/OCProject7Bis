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
