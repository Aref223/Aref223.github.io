from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from ..db import Base

class VisaRequirement(Base):
    __tablename__ = "visa_requirements"

    id = Column(Integer, primary_key=True)
    from_country = Column(String, index=True, nullable=False)
    to_country = Column(String, index=True, nullable=False)
    requirement = Column(String, nullable=False)
    source = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)