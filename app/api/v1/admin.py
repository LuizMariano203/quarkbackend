from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ... import models, schemas
from ...core import database, security

router = APIRouter()

@router.post("/set-balance", status_code=status.HTTP_204_NO_CONTENT)
def set_user_balance(
    request: schemas.AdminSetBalanceRequest,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(database.get_db)
):
    if current_user.id != 1:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    target_account = db.query(models.Account).filter(models.Account.owner_id == request.user_id).first()
    
    if not target_account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target user account not found")

    try:
        target_account.balance = request.new_balance
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Could not update balance")
    
    return

@router.post("/users/{user_id}/kyc", response_model=schemas.UserOut)
def updateUserKYCStatus(
    user_id: int,
    request: schemas.AdminUpdateKYCRequest,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(database.get_db)
):
    if current_user.id != 1:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    target_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target user not found")

    try:
        target_user.kyc_status = request.new_status
        db.commit()
        db.refresh(target_user)
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Could not update KYC status")

    return schemas.UserOut.from_orm(target_user)