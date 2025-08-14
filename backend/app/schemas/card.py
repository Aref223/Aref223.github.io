from pydantic import BaseModel, Field
from typing import Optional

class CardBase(BaseModel):
    name: str
    issuer: str
    network: Optional[str] = None
    annual_fee: Optional[float] = Field(default=None, ge=0)
    rewards: Optional[str] = None
    country: Optional[str] = None

class CardCreate(CardBase):
    pass

class CardUpdate(BaseModel):
    name: Optional[str] = None
    issuer: Optional[str] = None
    network: Optional[str] = None
    annual_fee: Optional[float] = Field(default=None, ge=0)
    rewards: Optional[str] = None
    country: Optional[str] = None

class CardOut(CardBase):
    id: int

    class Config:
        from_attributes = True