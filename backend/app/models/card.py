from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..db import Base

class Card(Base):
    __tablename__ = "cards"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    issuer = Column(String, index=True, nullable=False)
    network = Column(String, index=True, nullable=True)
    annual_fee = Column(Float, nullable=True)
    rewards = Column(String, nullable=True)  # JSON string of rewards summary
    country = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)