from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ...db import get_db
from ...models.scrape import ScrapeJob
from ..deps import get_current_user
from ...tasks.jobs import enqueue_card_scrape, enqueue_visa_scrape

router = APIRouter()

@router.post("/cards")
def trigger_cards_scrape(db: Session = Depends(get_db), _: object = Depends(get_current_user)):
    job = ScrapeJob(job_type="cards", status="pending", source="registry")
    db.add(job)
    db.commit()
    db.refresh(job)
    enqueue_card_scrape.delay(job.id)
    return {"job_id": job.id}

@router.post("/visas")
def trigger_visas_scrape(db: Session = Depends(get_db), _: object = Depends(get_current_user)):
    job = ScrapeJob(job_type="visas", status="pending", source="registry")
    db.add(job)
    db.commit()
    db.refresh(job)
    enqueue_visa_scrape.delay(job.id)
    return {"job_id": job.id}

@router.get("/jobs")
def list_jobs(db: Session = Depends(get_db), _: object = Depends(get_current_user)):
    jobs = db.query(ScrapeJob).order_by(ScrapeJob.created_at.desc()).limit(100).all()
    return [{"id": j.id, "type": j.job_type, "status": j.status, "source": j.source, "error": j.error, "created_at": j.created_at, "finished_at": j.finished_at} for j in jobs]