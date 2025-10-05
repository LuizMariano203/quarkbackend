from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

# Correção aplicada nas duas linhas abaixo
from ... import models, schemas
from ...core import database, security

router = APIRouter()

@router.post("/offers", response_model=schemas.CreditOfferOut, status_code=status.HTTP_201_CREATED)
def create_credit_offer(
    offer_in: schemas.CreditOfferCreate,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(database.get_db)
):
    if current_user.kyc_status != models.KYCStatus.VERIFIED:
        raise HTTPException(status_code=403, detail="User must be KYC verified to create offers")
        
    new_offer = models.CreditOffer(**offer_in.dict(), lender_id=current_user.id)
    db.add(new_offer)
    db.commit()
    db.refresh(new_offer)
    return new_offer

@router.get("/offers", response_model=List[schemas.CreditOfferOut])
def get_eligible_offers(
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(database.get_db)
):
    offers = db.query(models.CreditOffer).filter(
        models.CreditOffer.status == models.OfferStatus.ACTIVE,
        models.CreditOffer.lender_id != current_user.id
    ).all()
    return offers