"""
Scraping schemas for scraping job operations.

This module contains Pydantic models for scraping-related requests and responses
including job creation, updates, and scraping results.
"""

from pydantic import BaseModel, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.models.scraping_job import JobStatus, JobPriority

class ScrapingJobBase(BaseModel):
    """Base scraping job model with common fields."""
    job_name: str
    job_description: Optional[str] = None
    job_type: str
    target_urls: List[str]
    scraping_config: Dict[str, Any] = {}
    validation_config: Dict[str, Any] = {}
    priority: JobPriority = JobPriority.NORMAL

    @validator('job_name')
    def validate_job_name(cls, v):
        if not v or len(v.strip()) < 3:
            raise ValueError('Job name must be at least 3 characters long')
        return v.strip()

    @validator('target_urls')
    def validate_target_urls(cls, v):
        if not v or len(v) == 0:
            raise ValueError('At least one target URL is required')
        for url in v:
            if not url.startswith(('http://', 'https://')):
                raise ValueError('All URLs must start with http:// or https://')
        return v

    @validator('job_type')
    def validate_job_type(cls, v):
        allowed_types = ['visa', 'debit', 'credit', 'all']
        if v not in allowed_types:
            raise ValueError(f'Job type must be one of: {", ".join(allowed_types)}')
        return v

class ScrapingJobCreate(ScrapingJobBase):
    """Request model for scraping job creation."""
    max_retries: int = 3
    estimated_duration: Optional[int] = None

    @validator('max_retries')
    def validate_max_retries(cls, v):
        if v < 0 or v > 10:
            raise ValueError('Max retries must be between 0 and 10')
        return v

    @validator('estimated_duration')
    def validate_estimated_duration(cls, v):
        if v is not None and v < 0:
            raise ValueError('Estimated duration must be positive')
        return v

class ScrapingJobUpdate(BaseModel):
    """Request model for scraping job updates."""
    job_name: Optional[str] = None
    job_description: Optional[str] = None
    status: Optional[JobStatus] = None
    priority: Optional[JobPriority] = None
    scraping_config: Optional[Dict[str, Any]] = None
    validation_config: Optional[Dict[str, Any]] = None
    max_retries: Optional[int] = None

    @validator('job_name')
    def validate_job_name(cls, v):
        if v is not None and len(v.strip()) < 3:
            raise ValueError('Job name must be at least 3 characters long')
        return v.strip() if v else None

    @validator('max_retries')
    def validate_max_retries(cls, v):
        if v is not None and (v < 0 or v > 10):
            raise ValueError('Max retries must be between 0 and 10')
        return v

class ScrapingJobResponse(BaseModel):
    """Response model for scraping job information."""
    id: int
    job_name: str
    job_description: Optional[str]
    job_type: str
    target_urls: List[str]
    status: str
    priority: str
    progress: float
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    estimated_duration: Optional[int]
    actual_duration: Optional[int]
    total_cards_found: int
    valid_cards_found: int
    invalid_cards_found: int
    failed_scrapes: int
    success_rate: float
    error_message: Optional[str]
    retry_count: int
    max_retries: int
    processing_time_ms: Optional[int]
    memory_usage_mb: Optional[float]
    cpu_usage_percent: Optional[float]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

class ScrapingJobListResponse(BaseModel):
    """Response model for scraping job list."""
    jobs: List[ScrapingJobResponse]
    total: int
    page: int
    size: int
    pages: int
    stats: Dict[str, Any]

class ScrapingRequest(BaseModel):
    """Request model for immediate scraping."""
    urls: List[str]
    card_types: List[str] = ['visa', 'debit']
    validation_enabled: bool = True
    max_cards: Optional[int] = None
    timeout: int = 30

    @validator('urls')
    def validate_urls(cls, v):
        if not v or len(v) == 0:
            raise ValueError('At least one URL is required')
        for url in v:
            if not url.startswith(('http://', 'https://')):
                raise ValueError('All URLs must start with http:// or https://')
        return v

    @validator('card_types')
    def validate_card_types(cls, v):
        allowed_types = ['visa', 'debit', 'credit', 'mastercard', 'amex', 'discover']
        for card_type in v:
            if card_type not in allowed_types:
                raise ValueError(f'Card type must be one of: {", ".join(allowed_types)}')
        return v

    @validator('max_cards')
    def validate_max_cards(cls, v):
        if v is not None and v < 1:
            raise ValueError('Max cards must be at least 1')
        return v

    @validator('timeout')
    def validate_timeout(cls, v):
        if v < 10 or v > 300:
            raise ValueError('Timeout must be between 10 and 300 seconds')
        return v

class ScrapingResponse(BaseModel):
    """Response model for scraping results."""
    job_id: Optional[int]
    status: str
    total_cards_found: int
    valid_cards_found: int
    invalid_cards_found: int
    failed_urls: List[str]
    processing_time_ms: int
    cards: List[Dict[str, Any]]
    errors: List[str]
    warnings: List[str]

class ScrapingStats(BaseModel):
    """Scraping statistics model."""
    total_jobs: int
    running_jobs: int
    completed_jobs: int
    failed_jobs: int
    total_cards_scraped: int
    valid_cards_scraped: int
    average_success_rate: float
    average_processing_time: float
    recent_jobs: List[Dict[str, Any]]

class ScrapingJobSearchRequest(BaseModel):
    """Request model for scraping job search."""
    status: Optional[JobStatus] = None
    priority: Optional[JobPriority] = None
    job_type: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    page: int = 1
    size: int = 20

    @validator('job_type')
    def validate_job_type(cls, v):
        if v is not None:
            allowed_types = ['visa', 'debit', 'credit', 'all']
            if v not in allowed_types:
                raise ValueError(f'Job type must be one of: {", ".join(allowed_types)}')
        return v

    @validator('page', 'size')
    def validate_pagination(cls, v):
        if v < 1:
            raise ValueError('Page and size must be greater than 0')
        return v