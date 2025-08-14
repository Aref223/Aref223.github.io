# Backend

FastAPI backend with PostgreSQL/SQLite, Celery workers, and modular scrapers.

- Run local: `uvicorn app.main:app --reload` (after `pip install -r requirements.txt`)
- Tests: `pytest -q`
- Env: copy `../.env.example` to `../.env`