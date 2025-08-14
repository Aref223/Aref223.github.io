from celery import shared_task
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from ..db import SessionLocal
from ..models.scrape import ScrapeJob
from ..models.card import Card
from ..models.visa import VisaRequirement
from ..services.scraping.registry import get_card_scrapers, get_visa_scrapers

@shared_task(name="enqueue_card_scrape")
def enqueue_card_scrape(job_id: int) -> None:
    db: Session = SessionLocal()
    job = db.get(ScrapeJob, job_id)
    if not job:
        db.close()
        return
    job.status = "running"
    db.commit()
    try:
        total = 0
        for scraper in get_card_scrapers():
            for item in scraper.scrape():
                card = Card(**item)
                db.add(card)
                total += 1
        job.status = "completed"
        job.finished_at = datetime.now(tz=timezone.utc)
        db.commit()
    except Exception as exc:  # noqa: BLE001
        job.status = "failed"
        job.error = str(exc)
        job.finished_at = datetime.now(tz=timezone.utc)
        db.commit()
    finally:
        db.close()

@shared_task(name="enqueue_visa_scrape")
def enqueue_visa_scrape(job_id: int) -> None:
    db: Session = SessionLocal()
    job = db.get(ScrapeJob, job_id)
    if not job:
        db.close()
        return
    job.status = "running"
    db.commit()
    try:
        for scraper in get_visa_scrapers():
            for item in scraper.scrape():
                vis = VisaRequirement(**item)
                db.add(vis)
        job.status = "completed"
        job.finished_at = datetime.now(tz=timezone.utc)
        db.commit()
    except Exception as exc:  # noqa: BLE001
        job.status = "failed"
        job.error = str(exc)
        job.finished_at = datetime.now(tz=timezone.utc)
        db.commit()
    finally:
        db.close()