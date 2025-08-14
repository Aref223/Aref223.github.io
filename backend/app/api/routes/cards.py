from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from ...db import get_db
from ...models.card import Card
from ...schemas.card import CardCreate, CardUpdate, CardOut
from ..deps import get_current_user

router = APIRouter()

@router.get("/", response_model=list[CardOut])
def list_cards(
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
    q: str | None = Query(default=None),
    skip: int = 0,
    limit: int = Query(default=50, le=200),
):
    query = db.query(Card)
    if q:
        like = f"%{q}%"
        query = query.filter((Card.name.ilike(like)) | (Card.issuer.ilike(like)))
    return query.offset(skip).limit(limit).all()

@router.post("/", response_model=CardOut)
def create_card(card_in: CardCreate, db: Session = Depends(get_db), _: object = Depends(get_current_user)):
    card = Card(**card_in.model_dump())
    db.add(card)
    db.commit()
    db.refresh(card)
    return card

@router.get("/{card_id}", response_model=CardOut)
def get_card(card_id: int, db: Session = Depends(get_db), _: object = Depends(get_current_user)):
    card = db.get(Card, card_id)
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    return card

@router.put("/{card_id}", response_model=CardOut)
def update_card(card_id: int, card_in: CardUpdate, db: Session = Depends(get_db), _: object = Depends(get_current_user)):
    card = db.get(Card, card_id)
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    for k, v in card_in.model_dump(exclude_unset=True).items():
        setattr(card, k, v)
    db.commit()
    db.refresh(card)
    return card

@router.delete("/{card_id}")
def delete_card(card_id: int, db: Session = Depends(get_db), _: object = Depends(get_current_user)):
    card = db.get(Card, card_id)
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    db.delete(card)
    db.commit()
    return {"ok": True}