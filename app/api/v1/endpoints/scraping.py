"""
Scraping endpoints for web scraping operations.

This module provides API endpoints for scraping operations including
job management, immediate scraping, and scraping results.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
from typing import List, Dict, Any, Optional
import logging
import time

from app.database import get_db
from app.core.auth import get_current_user, get_current_scraper_user
from app.models.user import User, UserRole
from app.models.scraping_job import ScrapingJob, JobStatus, JobPriority
from app.models.card_data import CardData, CardType, CardStatus
from app.schemas.scraping import (
    ScrapingJobCreate,
    ScrapingJobUpdate,
    ScrapingJobResponse,
    ScrapingJobListResponse,
    ScrapingRequest,
    ScrapingResponse,
    ScrapingStats,
    ScrapingJobSearchRequest
)
from app.utils.scraping import ScrapingManager
from app.utils.validation import comprehensive_card_validation
from app.utils.security import validate_input, log_security_event, rate_limit

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/jobs", response_model=ScrapingJobResponse)
@rate_limit("scraping")
async def create_scraping_job(
    job_data: ScrapingJobCreate,
    request: Request,
    current_user: User = Depends(get_current_scraper_user),
    db: Session = Depends(get_db)
) -> ScrapingJobResponse:
    """Create a new scraping job."""
    try:
        # Validate URLs
        for url in job_data.target_urls:
            url_validation = validate_input(url, "url")
            if not url_validation["is_valid"]:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid URL: {url}")
        
        # Create scraping job
        job = ScrapingJob.create_job(
            user_id=current_user.id,
            job_name=job_data.job_name,
            job_type=job_data.job_type,
            target_urls=job_data.target_urls,
            scraping_config=job_data.scraping_config,
            validation_config=job_data.validation_config,
            priority=job_data.priority,
            max_retries=job_data.max_retries,
            estimated_duration=job_data.estimated_duration
        )
        
        db.add(job)
        db.commit()
        db.refresh(job)
        
        log_security_event("scraping_job_created", {
            "user_id": current_user.id,
            "job_id": job.id,
            "job_name": job.job_name,
            "target_urls_count": len(job_data.target_urls),
            "ip_address": request.client.host if request.client else "unknown"
        }, "info")
        
        return ScrapingJobResponse.from_orm(job)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating scraping job: {e}")
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create scraping job")

@router.get("/jobs", response_model=ScrapingJobListResponse)
async def get_scraping_jobs(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    status: Optional[JobStatus] = Query(None),
    priority: Optional[JobPriority] = Query(None),
    job_type: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get paginated list of scraping jobs."""
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
            "failed_jobs": db.query(ScrapingJob).filter(ScrapingJob.status == JobStatus.FAILED).count()
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
        logger.error(f"Error getting scraping jobs: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve scraping jobs")

@router.get("/jobs/{job_id}", response_model=ScrapingJobResponse)
async def get_scraping_job(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> ScrapingJobResponse:
    """Get scraping job by ID."""
    try:
        query = db.query(ScrapingJob).filter(ScrapingJob.id == job_id)
        
        # Users can only see their own jobs unless they're admin
        if current_user.role != UserRole.ADMIN:
            query = query.filter(ScrapingJob.user_id == current_user.id)
        
        job = query.first()
        if not job:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scraping job not found")
        
        return ScrapingJobResponse.from_orm(job)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting scraping job {job_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve scraping job")

@router.put("/jobs/{job_id}", response_model=ScrapingJobResponse)
async def update_scraping_job(
    job_id: int,
    job_data: ScrapingJobUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> ScrapingJobResponse:
    """Update scraping job."""
    try:
        query = db.query(ScrapingJob).filter(ScrapingJob.id == job_id)
        
        # Users can only update their own jobs unless they're admin
        if current_user.role != UserRole.ADMIN:
            query = query.filter(ScrapingJob.user_id == current_user.id)
        
        job = query.first()
        if not job:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scraping job not found")
        
        # Only allow updates if job is not running
        if job.status == JobStatus.RUNNING:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot update running job")
        
        # Update fields
        update_data = job_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(job, field, value)
        
        db.commit()
        db.refresh(job)
        
        log_security_event("scraping_job_updated", {
            "user_id": current_user.id,
            "job_id": job.id,
            "updated_fields": list(update_data.keys()),
            "ip_address": request.client.host if request.client else "unknown"
        }, "info")
        
        return ScrapingJobResponse.from_orm(job)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating scraping job {job_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update scraping job")

@router.delete("/jobs/{job_id}")
async def delete_scraping_job(
    job_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """Delete scraping job."""
    try:
        query = db.query(ScrapingJob).filter(ScrapingJob.id == job_id)
        
        # Users can only delete their own jobs unless they're admin
        if current_user.role != UserRole.ADMIN:
            query = query.filter(ScrapingJob.user_id == current_user.id)
        
        job = query.first()
        if not job:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scraping job not found")
        
        # Only allow deletion if job is not running
        if job.status == JobStatus.RUNNING:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete running job")
        
        job_name = job.job_name
        db.delete(job)
        db.commit()
        
        log_security_event("scraping_job_deleted", {
            "user_id": current_user.id,
            "job_id": job_id,
            "job_name": job_name,
            "ip_address": request.client.host if request.client else "unknown"
        }, "warning")
        
        return {"message": f"Scraping job '{job_name}' deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting scraping job {job_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete scraping job")

@router.post("/jobs/{job_id}/start")
async def start_scraping_job(
    job_id: int,
    background_tasks: BackgroundTasks,
    request: Request,
    current_user: User = Depends(get_current_scraper_user),
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """Start a scraping job."""
    try:
        query = db.query(ScrapingJob).filter(ScrapingJob.id == job_id)
        
        # Users can only start their own jobs unless they're admin
        if current_user.role != UserRole.ADMIN:
            query = query.filter(ScrapingJob.user_id == current_user.id)
        
        job = query.first()
        if not job:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scraping job not found")
        
        if job.status != JobStatus.PENDING:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Job is not in pending status")
        
        # Start the job
        job.start_job()
        db.commit()
        
        # Add background task for scraping
        background_tasks.add_task(run_scraping_job, job_id, current_user.id)
        
        log_security_event("scraping_job_started", {
            "user_id": current_user.id,
            "job_id": job.id,
            "job_name": job.job_name,
            "ip_address": request.client.host if request.client else "unknown"
        }, "info")
        
        return {"message": f"Scraping job '{job.job_name}' started successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting scraping job {job_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to start scraping job")

@router.post("/jobs/{job_id}/cancel")
async def cancel_scraping_job(
    job_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """Cancel a scraping job."""
    try:
        query = db.query(ScrapingJob).filter(ScrapingJob.id == job_id)
        
        # Users can only cancel their own jobs unless they're admin
        if current_user.role != UserRole.ADMIN:
            query = query.filter(ScrapingJob.user_id == current_user.id)
        
        job = query.first()
        if not job:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scraping job not found")
        
        if job.status not in [JobStatus.PENDING, JobStatus.RUNNING]:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Job cannot be cancelled")
        
        job.cancel_job()
        db.commit()
        
        log_security_event("scraping_job_cancelled", {
            "user_id": current_user.id,
            "job_id": job.id,
            "job_name": job.job_name,
            "ip_address": request.client.host if request.client else "unknown"
        }, "warning")
        
        return {"message": f"Scraping job '{job.job_name}' cancelled successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling scraping job {job_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to cancel scraping job")

@router.post("/scrape", response_model=ScrapingResponse)
@rate_limit("scraping")
async def scrape_immediately(
    scraping_data: ScrapingRequest,
    request: Request,
    current_user: User = Depends(get_current_scraper_user),
    db: Session = Depends(get_db)
) -> ScrapingResponse:
    """Perform immediate scraping without creating a job."""
    try:
        start_time = time.time()
        
        # Validate URLs
        for url in scraping_data.urls:
            url_validation = validate_input(url, "url")
            if not url_validation["is_valid"]:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid URL: {url}")
        
        # Initialize scraping manager
        scraping_manager = ScrapingManager()
        
        try:
            # Perform scraping
            scraped_cards = scraping_manager.scrape_cards(scraping_data.urls, scraping_data.card_types)
            
            # Limit results if specified
            if scraping_data.max_cards:
                scraped_cards = scraped_cards[:scraping_data.max_cards]
            
            # Process and validate cards
            processed_cards = []
            valid_cards = 0
            invalid_cards = 0
            errors = []
            warnings = []
            
            for card in scraped_cards:
                try:
                    # Validate card if enabled
                    if scraping_data.validation_enabled:
                        validation_result = comprehensive_card_validation(
                            card.card_number,
                            card.expiry_date or "",
                            card.cvv or "",
                            card.cardholder_name
                        )
                        
                        card_data = {
                            "card_number": card.card_number,
                            "card_type": card.card_type or "unknown",
                            "expiry_date": card.expiry_date,
                            "cvv": card.cvv,
                            "cardholder_name": card.cardholder_name,
                            "source_url": card.source_url,
                            "confidence_score": card.confidence_score,
                            "is_valid": validation_result["overall_valid"],
                            "validation_score": validation_result["score"],
                            "validation_errors": validation_result["errors"],
                            "validation_warnings": validation_result["warnings"]
                        }
                        
                        if validation_result["overall_valid"]:
                            valid_cards += 1
                        else:
                            invalid_cards += 1
                    else:
                        card_data = {
                            "card_number": card.card_number,
                            "card_type": card.card_type or "unknown",
                            "expiry_date": card.expiry_date,
                            "cvv": card.cvv,
                            "cardholder_name": card.cardholder_name,
                            "source_url": card.source_url,
                            "confidence_score": card.confidence_score,
                            "is_valid": None,
                            "validation_score": None,
                            "validation_errors": [],
                            "validation_warnings": []
                        }
                    
                    processed_cards.append(card_data)
                    
                except Exception as e:
                    errors.append(f"Error processing card {card.card_number}: {str(e)}")
            
            processing_time = int((time.time() - start_time) * 1000)
            
            log_security_event("immediate_scraping_completed", {
                "user_id": current_user.id,
                "urls_count": len(scraping_data.urls),
                "cards_found": len(scraped_cards),
                "valid_cards": valid_cards,
                "invalid_cards": invalid_cards,
                "processing_time_ms": processing_time,
                "ip_address": request.client.host if request.client else "unknown"
            }, "info")
            
            return ScrapingResponse(
                job_id=None,
                status="completed",
                total_cards_found=len(scraped_cards),
                valid_cards_found=valid_cards,
                invalid_cards_found=invalid_cards,
                failed_urls=[],
                processing_time_ms=processing_time,
                cards=processed_cards,
                errors=errors,
                warnings=warnings
            )
            
        finally:
            scraping_manager.close()
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in immediate scraping: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Scraping failed")

@router.get("/stats", response_model=ScrapingStats)
async def get_scraping_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> ScrapingStats:
    """Get scraping statistics."""
    try:
        query = db.query(ScrapingJob)
        
        # Users can only see their own stats unless they're admin
        if current_user.role != UserRole.ADMIN:
            query = query.filter(ScrapingJob.user_id == current_user.id)
        
        total_jobs = query.count()
        running_jobs = query.filter(ScrapingJob.status == JobStatus.RUNNING).count()
        completed_jobs = query.filter(ScrapingJob.status == JobStatus.COMPLETED).count()
        failed_jobs = query.filter(ScrapingJob.status == JobStatus.FAILED).count()
        
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
        
        return ScrapingStats(
            total_jobs=total_jobs,
            running_jobs=running_jobs,
            completed_jobs=completed_jobs,
            failed_jobs=failed_jobs,
            total_cards_scraped=total_cards_scraped,
            valid_cards_scraped=valid_cards_scraped,
            average_success_rate=average_success_rate,
            average_processing_time=average_processing_time,
            recent_jobs=recent_jobs_data
        )
    except Exception as e:
        logger.error(f"Error getting scraping stats: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve scraping statistics")

async def run_scraping_job(job_id: int, user_id: int):
    """Background task to run a scraping job."""
    from app.database import SessionLocal
    
    db = SessionLocal()
    try:
        job = db.query(ScrapingJob).filter(ScrapingJob.id == job_id).first()
        if not job:
            logger.error(f"Scraping job {job_id} not found")
            return
        
        scraping_manager = ScrapingManager()
        
        try:
            # Perform scraping
            scraped_cards = scraping_manager.scrape_cards(job.target_urls, [job.job_type])
            
            # Process and store cards
            for card in scraped_cards:
                try:
                    # Validate card
                    validation_result = comprehensive_card_validation(
                        card.card_number,
                        card.expiry_date or "",
                        card.cvv or "",
                        card.cardholder_name
                    )
                    
                    # Create card data record
                    card_data = CardData.create_card_data(
                        user_id=user_id,
                        card_number=card.card_number,
                        card_type=CardType(card.card_type) if card.card_type else CardType.UNKNOWN,
                        expiry_date=card.expiry_date,
                        cvv=card.cvv,
                        cardholder_name=card.cardholder_name,
                        scraping_job_id=job_id,
                        source_url=card.source_url,
                        bank_name=card.bank_name
                    )
                    
                    # Update validation status
                    card_data.update_validation_status(
                        validation_result["overall_valid"],
                        validation_result["score"],
                        validation_result["errors"],
                        validation_result["warnings"]
                    )
                    
                    db.add(card_data)
                    
                    # Update job statistics
                    job.increment_card_count(validation_result["overall_valid"])
                    
                except Exception as e:
                    logger.error(f"Error processing card in job {job_id}: {e}")
                    job.increment_failed_scrapes()
            
            # Complete the job
            job.complete_job()
            db.commit()
            
            logger.info(f"Scraping job {job_id} completed successfully")
            
        finally:
            scraping_manager.close()
            
    except Exception as e:
        logger.error(f"Error running scraping job {job_id}: {e}")
        if job:
            job.fail_job(str(e))
            db.commit()
    finally:
        db.close()