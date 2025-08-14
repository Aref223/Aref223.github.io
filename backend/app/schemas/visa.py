from pydantic import BaseModel

class VisaBase(BaseModel):
    from_country: str
    to_country: str
    requirement: str
    source: str | None = None

class VisaCreate(VisaBase):
    pass

class VisaOut(VisaBase):
    id: int

    class Config:
        from_attributes = True