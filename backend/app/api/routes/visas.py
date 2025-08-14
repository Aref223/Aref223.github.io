from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from ...db import get_db
from ...models.visa import VisaRequirement
from ...schemas.visa import VisaCreate, VisaOut
from ..deps import get_current_user

router = APIRouter()

@router.get("/", response_model=list[VisaOut])
def list_visas(
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
    from_country: str | None = Query(default=None),
    to_country: str | None = Query(default=None),
    skip: int = 0,
    limit: int = Query(default=50, le=200),
):
    query = db.query(VisaRequirement)
    if from_country:
        query = query.filter(VisaRequirement.from_country == from_country)
    if to_country:
        query = query.filter(VisaRequirement.to_country == to_country)
    return query.offset(skip).limit(limit).all()

@router.post("/", response_model=VisaOut)
def create_visa(visa_in: VisaCreate, db: Session = Depends(get_db), _: object = Depends(get_current_user)):
    visa = VisaRequirement(**visa_in.model_dump())
    db.add(visa)
    db.commit()
    db.refresh(visa)
    return visa

@router.get("/{visa_id}", response_model=VisaOut)
def get_visa(visa_id: int, db: Session = Depends(get_db), _: object = Depends(get_current_user)):
    visa = db.get(VisaRequirement, visa_id)
    if not visa:
        raise HTTPException(status_code=404, detail="Visa entry not found")
    return visa

@router.delete("/{visa_id}")
def delete_visa(visa_id: int, db: Session = Depends(get_db), _: object = Depends(get_current_user)):
    visa = db.get(VisaRequirement, visa_id)
    if not visa:
        raise HTTPException(status_code=404, detail="Visa entry not found")
    db.delete(visa)
    db.commit()
    return {"ok": True}