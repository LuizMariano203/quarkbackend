# app/api/v1/wallet.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List 
from ... import models, schemas
from ...core import database, security
from sqlalchemy import or_

router = APIRouter()

@router.get(
    "/balance", 
    response_model=schemas.AccountOut,
    summary="Obter Saldo da Carteira",
    description="Retorna o saldo disponível e o status da conta do usuário autenticado."
)
def get_balance(current_user: models.User = Depends(security.get_current_user), db: Session = Depends(database.get_db)):
    account = db.query(models.Account).filter(models.Account.owner_id == current_user.id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return account

@router.get(
    "/transaction/history",
    response_model=List[schemas.TransactionOut],
    summary="Histórico de Transações",
    description="Lista todas as transações (débito e crédito) associadas à carteira do usuário autenticado."
)
def get_transaction_history(
    current_user: models.User = Depends(security.get_current_user), 
    db: Session = Depends(database.get_db)
):
    account = db.query(models.Account).filter(models.Account.owner_id == current_user.id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
        
    # Busca transações onde a carteira é origem OU destino
    transactions = db.query(models.Transaction).filter(
        or_(
            models.Transaction.origin_account_id == account.id, 
            models.Transaction.destination_account_id == account.id
        )
    ).order_by(models.Transaction.timestamp_utc.desc()).all()
    
    return transactions


@router.post("/transfer", status_code=status.HTTP_204_NO_CONTENT)
def p2p_transfer(transfer_data: schemas.TransferRequest, current_user: models.User = Depends(security.get_current_user), db: Session = Depends(database.get_db)):
    if transfer_data.amount <= 0:
        raise HTTPException(status_code=400, detail="Transfer amount must be positive")

    try:
        # Bloqueia as contas para transação atômica
        source_account = db.query(models.Account).filter(models.Account.owner_id == current_user.id).with_for_update().first()
        
        if source_account.balance < transfer_data.amount:
            raise HTTPException(status_code=400, detail="Insufficient funds")

        destination_account = db.query(models.Account).filter(models.Account.owner_id == transfer_data.destination_user_id).with_for_update().first()
        if not destination_account:
            raise HTTPException(status_code=404, detail="Destination user not found")

        # 1. Atualização de Saldos
        source_account.balance -= transfer_data.amount
        destination_account.balance += transfer_data.amount
        
        # 2. Criação do Registro de Transação (Ledger)
        # Registramos APENAS o evento de débito P2P, e o histórico usa a coluna de destino para inferir o crédito.
        tx_debit = models.Transaction(
            type=models.TransactionType.P2P_DEBITO,
            value=transfer_data.amount,
            origin_account_id=source_account.id,
            destination_account_id=destination_account.id
        )
        db.add(tx_debit)
        
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        print(f"Erro na transferência P2P: {e}")
        raise HTTPException(status_code=500, detail="Transfer failed")
        
    return