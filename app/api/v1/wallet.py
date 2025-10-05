from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ... import models, schemas
from ...core import database, security

router = APIRouter()

@router.get("/balance", response_model=schemas.AccountOut)
def get_balance(current_user: models.User = Depends(security.get_current_user), db: Session = Depends(database.get_db)):
    account = db.query(models.Account).filter(models.Account.owner_id == current_user.id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return account

@router.post("/transfer", status_code=status.HTTP_204_NO_CONTENT)
def p2p_transfer(transfer_data: schemas.TransferRequest, current_user: models.User = Depends(security.get_current_user), db: Session = Depends(database.get_db)):
    if transfer_data.amount <= 0:
        raise HTTPException(status_code=400, detail="Transfer amount must be positive")

    source_account = db.query(models.Account).filter(models.Account.owner_id == current_user.id).first()
    if source_account.balance < transfer_data.amount:
        raise HTTPException(status_code=400, detail="Insufficient funds")

    destination_account = db.query(models.Account).filter(models.Account.owner_id == transfer_data.destination_user_id).first()
    if not destination_account:
        raise HTTPException(status_code=404, detail="Destination user not found")

    # Início do bloco transacional explícito
    try:
        source_account.balance -= transfer_data.amount
        destination_account.balance += transfer_data.amount
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Transfer failed")
        
    return