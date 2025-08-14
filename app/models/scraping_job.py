"""
Scraping job model for tracking scraping operations and their status.

This module defines the ScrapingJob model for managing scraping operations,
including job status, progress tracking, and result management.
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Enum, JSON, ForeignKey, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
from datetime import datetime
from typing import Optional, Dict, Any

from app.database import Base


class JobStatus(str, enum.Enum):
    """Job status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class JobPriority(str, enum.Enum):
    """Job priority enumeration."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class ScrapingJob(Base):
    """
    Scraping job model for tracking scraping operations and their status.
    
    This model includes comprehensive job tracking, progress monitoring,
    and result management for scraping operations.
    """
    
    __tablename__ = "scraping_jobs"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign keys
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Job identification
    job_name = Column(String(200), nullable=False)
    job_description = Column(Text)
    job_type = Column(String(100), nullable=False)  # "visa_scraper", "debit_scraper", etc.
    
    # Job configuration
    target_urls = Column(JSON, nullable=False)  # List of URLs to scrape
    scraping_config = Column(JSON, default=dict)  # Scraping parameters
    validation_config = Column(JSON, default=dict)  # Validation parameters
    
    # Job status and progress
    status = Column(Enum(JobStatus), default=JobStatus.PENDING, nullable=False)
    priority = Column(Enum(JobPriority), default=JobPriority.NORMAL, nullable=False)
    progress = Column(Float, default=0.0)  # 0.0 to 100.0
    
    # Execution tracking
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    estimated_duration = Column(Integer)  # in seconds
    actual_duration = Column(Integer)  # in seconds
    
    # Results and statistics
    total_cards_found = Column(Integer, default=0)
    valid_cards_found = Column(Integer, default=0)
    invalid_cards_found = Column(Integer, default=0)
    failed_scrapes = Column(Integer, default=0)
    
    # Error handling
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    
    # Performance metrics
    processing_time_ms = Column(Integer)
    memory_usage_mb = Column(Float)
    cpu_usage_percent = Column(Float)
    
    # Security and audit
    ip_address = Column(String(45))
    user_agent = Column(Text)
    session_id = Column(String(255))
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="scraping_jobs")
    card_data = relationship("CardData", back_populates="scraping_job")
    
    def __repr__(self):
        return f"<ScrapingJob(id={self.id}, name='{self.job_name}', status='{self.status}')>"
    
    @property
    def is_running(self) -> bool:
        """Check if job is currently running."""
        return self.status == JobStatus.RUNNING
    
    @property
    def is_completed(self) -> bool:
        """Check if job is completed."""
        return self.status == JobStatus.COMPLETED
    
    @property
    def is_failed(self) -> bool:
        """Check if job has failed."""
        return self.status == JobStatus.FAILED
    
    @property
    def can_retry(self) -> bool:
        """Check if job can be retried."""
        return self.retry_count < self.max_retries and self.status == JobStatus.FAILED
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate of the job."""
        total = self.total_cards_found + self.failed_scrapes
        if total == 0:
            return 0.0
        return (self.total_cards_found / total) * 100
    
    def start_job(self) -> None:
        """Mark job as started."""
        self.status = JobStatus.RUNNING
        self.started_at = datetime.utcnow()
        self.progress = 0.0
    
    def complete_job(self) -> None:
        """Mark job as completed."""
        self.status = JobStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        self.progress = 100.0
        
        if self.started_at:
            self.actual_duration = int((self.completed_at - self.started_at).total_seconds())
    
    def fail_job(self, error_message: str) -> None:
        """
        Mark job as failed with error message.
        
        Args:
            error_message: Description of the failure
        """
        self.status = JobStatus.FAILED
        self.completed_at = datetime.utcnow()
        self.error_message = error_message
        self.retry_count += 1
        
        if self.started_at:
            self.actual_duration = int((self.completed_at - self.started_at).total_seconds())
    
    def cancel_job(self) -> None:
        """Cancel the job."""
        self.status = JobStatus.CANCELLED
        self.completed_at = datetime.utcnow()
        
        if self.started_at:
            self.actual_duration = int((self.completed_at - self.started_at).total_seconds())
    
    def pause_job(self) -> None:
        """Pause the job."""
        self.status = JobStatus.PAUSED
    
    def resume_job(self) -> None:
        """Resume a paused job."""
        if self.status == JobStatus.PAUSED:
            self.status = JobStatus.RUNNING
    
    def update_progress(self, progress: float) -> None:
        """
        Update job progress.
        
        Args:
            progress: Progress percentage (0.0 to 100.0)
        """
        self.progress = max(0.0, min(100.0, progress))
    
    def increment_card_count(self, is_valid: bool = True) -> None:
        """
        Increment card count statistics.
        
        Args:
            is_valid: Whether the card is valid
        """
        self.total_cards_found += 1
        if is_valid:
            self.valid_cards_found += 1
        else:
            self.invalid_cards_found += 1
    
    def increment_failed_scrapes(self) -> None:
        """Increment failed scrape count."""
        self.failed_scrapes += 1
    
    def update_performance_metrics(self, processing_time_ms: int, memory_usage_mb: float, cpu_usage_percent: float) -> None:
        """
        Update performance metrics.
        
        Args:
            processing_time_ms: Processing time in milliseconds
            memory_usage_mb: Memory usage in MB
            cpu_usage_percent: CPU usage percentage
        """
        self.processing_time_ms = processing_time_ms
        self.memory_usage_mb = memory_usage_mb
        self.cpu_usage_percent = cpu_usage_percent
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert job to dictionary representation.
        
        Returns:
            dict: Job data as dictionary
        """
        return {
            "id": self.id,
            "job_name": self.job_name,
            "job_description": self.job_description,
            "job_type": self.job_type,
            "status": self.status.value,
            "priority": self.priority.value,
            "progress": self.progress,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "estimated_duration": self.estimated_duration,
            "actual_duration": self.actual_duration,
            "total_cards_found": self.total_cards_found,
            "valid_cards_found": self.valid_cards_found,
            "invalid_cards_found": self.invalid_cards_found,
            "failed_scrapes": self.failed_scrapes,
            "success_rate": self.success_rate,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "processing_time_ms": self.processing_time_ms,
            "memory_usage_mb": self.memory_usage_mb,
            "cpu_usage_percent": self.cpu_usage_percent,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def create_job(
        cls,
        user_id: int,
        job_name: str,
        job_type: str,
        target_urls: list,
        scraping_config: dict = None,
        validation_config: dict = None,
        priority: JobPriority = JobPriority.NORMAL,
        **kwargs
    ) -> "ScrapingJob":
        """
        Create a new scraping job.
        
        Args:
            user_id: ID of the user creating the job
            job_name: Name of the job
            job_type: Type of scraping job
            target_urls: List of URLs to scrape
            scraping_config: Scraping configuration
            validation_config: Validation configuration
            priority: Job priority
            **kwargs: Additional job attributes
            
        Returns:
            ScrapingJob: Newly created job instance
        """
        return cls(
            user_id=user_id,
            job_name=job_name,
            job_type=job_type,
            target_urls=target_urls,
            scraping_config=scraping_config or {},
            validation_config=validation_config or {},
            priority=priority,
            **kwargs
        )