import os
import sys
import tempfile
import pytest

# Ensure backend root is importable
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app import db as db_module  # noqa: E402
from app.db import Base  # noqa: E402
from app.tasks import jobs as job_tasks  # noqa: E402

@pytest.fixture(autouse=True)
def _isolate_db(monkeypatch):
    fd, path = tempfile.mkstemp(prefix="testdb_", suffix=".sqlite")
    os.close(fd)
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{path}")

    # Recreate engine and SessionLocal with new DATABASE_URL
    from importlib import reload
    reload(db_module)

    # Create tables
    Base.metadata.create_all(bind=db_module.engine)

    # Make celery tasks execute synchronously during tests
    original_card = job_tasks.enqueue_card_scrape
    original_visa = job_tasks.enqueue_visa_scrape

    def _sync_card(job_id: int):
        return original_card.run(job_id) if hasattr(original_card, 'run') else original_card(job_id)

    def _sync_visa(job_id: int):
        return original_visa.run(job_id) if hasattr(original_visa, 'run') else original_visa(job_id)

    job_tasks.enqueue_card_scrape.delay = _sync_card
    job_tasks.enqueue_visa_scrape.delay = _sync_visa

    yield

    try:
        os.remove(path)
    except FileNotFoundError:
        pass