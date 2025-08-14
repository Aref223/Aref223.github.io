"""
Jobs endpoints for job management operations.

This module provides API endpoints for job management including
job creation, updates, retrieval, and job monitoring.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
from typing import List, Dict, Any, Optional
import logging

from app.database import get_db
from app.core.auth import get_current_user
from app.models.user import User, UserRole
from app.models.scraping_job import ScrapingJob, JobStatus, JobPriority
from app.schemas.scraping import (
    ScrapingJobCreate,
    ScrapingJobUpdate,
    ScrapingJobResponse,
    ScrapingJobListResponse,
    ScrapingJobSearchRequest
)
from app.utils.security import validate_input, log_security_event

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/", response_model=ScrapingJobListResponse)
async def get_jobs(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    status: Optional[JobStatus] = Query(None),
    priority: Optional[JobPriority] = Query(None),
    job_type: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get paginated list of jobs with optional filtering."""
    try:
        query = db.query(ScrapingJob)
        
        # Users can only see their own jobs unless they're admin
        if current_user.role != UserRole.ADMIN:
            query = query.filter(ScrapingJob.user_id == current_user.id)
        
        # Apply filters
        if status:
            query = query.filter(ScrapingJob.status == status)
        if priority:
            query = query.filter(ScrapingJob.priority == priority)
        if job_type:
            query = query.filter(ScrapingJob.job_type == job_type)
        
        # Get total count
        total = query.count()
        
        # Apply pagination and ordering
        jobs = query.order_by(desc(ScrapingJob.created_at)).offset((page - 1) * size).limit(size).all()
        
        # Calculate pagination info
        pages = (total + size - 1) // size
        
        # Calculate stats
        stats = {
            "total_jobs": total,
            "running_jobs": db.query(ScrapingJob).filter(ScrapingJob.status == JobStatus.RUNNING).count(),
            "completed_jobs": db.query(ScrapingJob).filter(ScrapingJob.status == JobStatus.COMPLETED).count(),
            "failed_jobs": db.query(ScrapingJob).filter(ScrapingJob.status == JobStatus.FAILED).count(),
            "pending_jobs": db.query(ScrapingJob).filter(ScrapingJob.status == JobStatus.PENDING).count()
        }
        
        return {
            "jobs": [ScrapingJobResponse.from_orm(job) for job in jobs],
            "total": total,
            "page": page,
            "size": size,
            "pages": pages,
            "stats": stats
        }
    except Exception as e:
        logger.error(f"Error getting jobs: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve jobs")

@router.get("/{job_id}", response_model=ScrapingJobResponse)
async def get_job(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> ScrapingJobResponse:
    """Get job by ID."""
    try:
        query = db.query(ScrapingJob).filter(ScrapingJob.id == job_id)
        
        # Users can only see their own jobs unless they're admin
        if current_user.role != UserRole.ADMIN:
            query = query.filter(ScrapingJob.user_id == current_user.id)
        
        job = query.first()
        if not job:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
        
        return ScrapingJobResponse.from_orm(job)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job {job_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve job")

@router.put("/{job_id}", response_model=ScrapingJobResponse)
async def update_job(
    job_id: int,
    job_data: ScrapingJobUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> ScrapingJobResponse:
    """Update job information."""
    try:
        query = db.query(ScrapingJob).filter(ScrapingJob.id == job_id)
        
        # Users can only update their own jobs unless they're admin
        if current_user.role != UserRole.ADMIN:
            query = query.filter(ScrapingJob.user_id == current_user.id)
        
        job = query.first()
        if not job:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
        
        # Only allow updates if job is not running
        if job.status == JobStatus.RUNNING:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot update running job")
        
        # Update fields
        update_data = job_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(job, field, value)
        
        db.commit()
        db.refresh(job)
        
        log_security_event("job_updated", {
            "user_id": current_user.id,
            "job_id": job.id,
            "updated_fields": list(update_data.keys()),
            "ip_address": request.client.host if request.client else "unknown"
        }, "info")
        
        return ScrapingJobResponse.from_orm(job)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating job {job_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update job")

@router.delete("/{job_id}")
async def delete_job(
    job_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """Delete job."""
    try:
        query = db.query(ScrapingJob).filter(ScrapingJob.id == job_id)
        
        # Users can only delete their own jobs unless they're admin
        if current_user.role != UserRole.ADMIN:
            query = query.filter(ScrapingJob.user_id == current_user.id)
        
        job = query.first()
        if not job:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
        
        # Only allow deletion if job is not running
        if job.status == JobStatus.RUNNING:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete running job")
        
        job_name = job.job_name
        db.delete(job)
        db.commit()
        
        log_security_event("job_deleted", {
            "user_id": current_user.id,
            "job_id": job_id,
            "job_name": job_name,
            "ip_address": request.client.host if request.client else "unknown"
        }, "warning")
        
        return {"message": f"Job '{job_name}' deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting job {job_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete job")

@router.post("/{job_id}/pause")
async def pause_job(
    job_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """Pause a running job."""
    try:
        query = db.query(ScrapingJob).filter(ScrapingJob.id == job_id)
        
        # Users can only pause their own jobs unless they're admin
        if current_user.role != UserRole.ADMIN:
            query = query.filter(ScrapingJob.user_id == current_user.id)
        
        job = query.first()
        if not job:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
        
        if job.status != JobStatus.RUNNING:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only running jobs can be paused")
        
        job.pause_job()
        db.commit()
        
        log_security_event("job_paused", {
            "user_id": current_user.id,
            "job_id": job.id,
            "job_name": job.job_name,
            "ip_address": request.client.host if request.client else "unknown"
        }, "info")
        
        return {"message": f"Job '{job.job_name}' paused successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error pausing job {job_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to pause job")

@router.post("/{job_id}/resume")
async def resume_job(
    job_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """Resume a paused job."""
    try:
        query = db.query(ScrapingJob).filter(ScrapingJob.id == job_id)
        
        # Users can only resume their own jobs unless they're admin
        if current_user.role != UserRole.ADMIN:
            query = query.filter(ScrapingJob.user_id == current_user.id)
        
        job = query.first()
        if not job:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
        
        if job.status != JobStatus.PAUSED:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only paused jobs can be resumed")
        
        job.resume_job()
        db.commit()
        
        log_security_event("job_resumed", {
            "user_id": current_user.id,
            "job_id": job.id,
            "job_name": job.job_name,
            "ip_address": request.client.host if request.client else "unknown"
        }, "info")
        
        return {"message": f"Job '{job.job_name}' resumed successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resuming job {job_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to resume job")

@router.post("/{job_id}/retry")
async def retry_job(
    job_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """Retry a failed job."""
    try:
        query = db.query(ScrapingJob).filter(ScrapingJob.id == job_id)
        
        # Users can only retry their own jobs unless they're admin
        if current_user.role != UserRole.ADMIN:
            query = query.filter(ScrapingJob.user_id == current_user.id)
        
        job = query.first()
        if not job:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
        
        if job.status != JobStatus.FAILED:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only failed jobs can be retried")
        
        if job.retry_count >= job.max_retries:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Job has exceeded maximum retry attempts")
        
        # Reset job status for retry
        job.status = JobStatus.PENDING
        job.error_message = None
        job.progress = 0.0
        job.started_at = None
        job.completed_at = None
        job.actual_duration = None
        
        db.commit()
        
        log_security_event("job_retried", {
            "user_id": current_user.id,
            "job_id": job.id,
            "job_name": job.job_name,
            "retry_count": job.retry_count,
            "ip_address": request.client.host if request.client else "unknown"
        }, "info")
        
        return {"message": f"Job '{job.job_name}' queued for retry"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrying job {job_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retry job")

@router.get("/stats/overview")
async def get_job_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get job statistics."""
    try:
        query = db.query(ScrapingJob)
        
        # Users can only see their own stats unless they're admin
        if current_user.role != UserRole.ADMIN:
            query = query.filter(ScrapingJob.user_id == current_user.id)
        
        total_jobs = query.count()
        running_jobs = query.filter(ScrapingJob.status == JobStatus.RUNNING).count()
        completed_jobs = query.filter(ScrapingJob.status == JobStatus.COMPLETED).count()
        failed_jobs = query.filter(ScrapingJob.status == JobStatus.FAILED).count()
        pending_jobs = query.filter(ScrapingJob.status == JobStatus.PENDING).count()
        paused_jobs = query.filter(ScrapingJob.status == JobStatus.PAUSED).count()
        
        # Calculate totals
        total_cards_scraped = sum(job.total_cards_found for job in query.all())
        valid_cards_scraped = sum(job.valid_cards_found for job in query.all())
        
        # Calculate averages
        completed_jobs_list = query.filter(ScrapingJob.status == JobStatus.COMPLETED).all()
        if completed_jobs_list:
            average_success_rate = sum(job.success_rate for job in completed_jobs_list) / len(completed_jobs_list)
            average_processing_time = sum(job.actual_duration or 0 for job in completed_jobs_list) / len(completed_jobs_list)
        else:
            average_success_rate = 0.0
            average_processing_time = 0.0
        
        # Get recent jobs
        recent_jobs = query.order_by(desc(ScrapingJob.created_at)).limit(5).all()
        recent_jobs_data = [
            {
                "id": job.id,
                "name": job.job_name,
                "status": job.status.value,
                "total_cards": job.total_cards_found,
                "valid_cards": job.valid_cards_found,
                "created_at": job.created_at.isoformat() if job.created_at else None
            }
            for job in recent_jobs
        ]
        
        return {
            "total_jobs": total_jobs,
            "running_jobs": running_jobs,
            "completed_jobs": completed_jobs,
            "failed_jobs": failed_jobs,
            "pending_jobs": pending_jobs,
            "paused_jobs": paused_jobs,
            "total_cards_scraped": total_cards_scraped,
            "valid_cards_scraped": valid_cards_scraped,
            "average_success_rate": average_success_rate,
            "average_processing_time": average_processing_time,
            "recent_jobs": recent_jobs_data
        }
    except Exception as e:
        logger.error(f"Error getting job stats: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve job statistics")

@router.post("/search", response_model=ScrapingJobListResponse)
async def search_jobs(
    search_request: ScrapingJobSearchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Search jobs with advanced filters."""
    try:
        query = db.query(ScrapingJob)
        
        # Users can only search their own jobs unless they're admin
        if current_user.role != UserRole.ADMIN:
            query = query.filter(ScrapingJob.user_id == current_user.id)
        
        # Apply filters
        if search_request.status:
            query = query.filter(ScrapingJob.status == search_request.status)
        if search_request.priority:
            query = query.filter(ScrapingJob.priority == search_request.priority)
        if search_request.job_type:
            query = query.filter(ScrapingJob.job_type == search_request.job_type)
        if search_request.date_from:
            query = query.filter(ScrapingJob.created_at >= search_request.date_from)
        if search_request.date_to:
            query = query.filter(ScrapingJob.created_at <= search_request.date_to)
        
        # Get total count
        total = query.count()
        
        # Apply pagination and ordering
        jobs = query.order_by(desc(ScrapingJob.created_at)).offset((search_request.page - 1) * search_request.size).limit(search_request.size).all()
        
        # Calculate pagination info
        pages = (total + search_request.size - 1) // search_request.size
        
        # Calculate stats
        stats = {
            "total_jobs": total,
            "running_jobs": query.filter(ScrapingJob.status == JobStatus.RUNNING).count(),
            "completed_jobs": query.filter(ScrapingJob.status == JobStatus.COMPLETED).count(),
            "failed_jobs": query.filter(ScrapingJob.status == JobStatus.FAILED).count()
        }
        
        return {
            "jobs": [ScrapingJobResponse.from_orm(job) for job in jobs],
            "total": total,
            "page": search_request.page,
            "size": search_request.size,
            "pages": pages,
            "stats": stats
        }
    except Exception as e:
        logger.error(f"Error searching jobs: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to search jobs")