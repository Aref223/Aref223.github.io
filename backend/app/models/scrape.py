from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.sql import func
from ..db import Base

class ScrapeJob(Base):
    __tablename__ = "scrape_jobs"

    id = Column(Integer, primary_key=True)
    job_type = Column(String, nullable=False)  # 'cards' or 'visas'
    status = Column(String, nullable=False, default="pending")  # pending, running, completed, failed
    source = Column(String, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    finished_at = Column(DateTime(timezone=True), nullable=True)