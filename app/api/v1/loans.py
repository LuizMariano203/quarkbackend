from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import date
from dateutil.relativedelta import relativedelta
# Importa Decimal para garantir cálculos monetários precisos
from decimal import Decimal

from ... import models, schemas
from ...core import database, security

router = APIRouter()

@router.post("/offers/{offer_id}/accept", response_model=schemas.LoanOut, status_code=status.HTTP_201_CREATED)
def accept_offer(
    offer_id: int,
    request: schemas.AcceptOfferRequest,
    borrower: models.User = Depends(security.get_current_user),
    db: Session = Depends(database.get_db)
):
    if borrower.kyc_status != models.KYCStatus.VERIFIED:
        raise HTTPException(status_code=403, detail="User must be KYC verified to accept offers")

    # Início do bloco transacional explícito para garantir atomicidade.
    try:
        # 1. Busca e Bloqueio da Oferta
        offer = db.query(models.CreditOffer).filter(models.CreditOffer.id == offer_id).with_for_update().first()

        if not offer or offer.status != models.OfferStatus.ACTIVE:
            raise HTTPException(status_code=404, detail="Offer not found or not active")
        
        # 2. Validações
        if request.amount > offer.max_amount:
            raise HTTPException(status_code=400, detail="Requested amount exceeds offer maximum")
        
        if borrower.id == offer.lender_id:
             raise HTTPException(status_code=400, detail="Cannot accept your own offer")

        # 3. Busca e Bloqueio das Contas
        lender_account = db.query(models.Account).filter(models.Account.owner_id == offer.lender_id).with_for_update().first()
        if lender_account.balance < request.amount:
            raise HTTPException(status_code=400, detail="Lender has insufficient funds")
        
        borrower_account = db.query(models.Account).filter(models.Account.owner_id == borrower.id).with_for_update().first()
        
        # 4. Atualiza o Status da Oferta
        offer.status = models.OfferStatus.COMMITTED
        
        # 5. Cria o Novo Empréstimo
        new_loan = models.Loan(
            borrower_id=borrower.id,
            lender_id=offer.lender_id,
            credit_offer_id=offer.id,
            amount=request.amount,
            interest_rate=offer.interest_rate,
            term_months=offer.term_months
        )
        db.add(new_loan)
        db.flush()

        # 6. Calcula e Cria as Parcelas (Installments)
        # CORREÇÃO CRÍTICA: Garante que a divisão resulte em um Decimal,
        # evitando o erro 'unsupported operand type(s) for *: decimal.Decimal and float'.
        term_factor = Decimal(new_loan.term_months) / Decimal(12)
        
        total_interest = new_loan.amount * new_loan.interest_rate * term_factor
        total_repayment = new_loan.amount + total_interest
        
        # Garante que a divisão para o valor da parcela também seja segura
        installment_amount = total_repayment / Decimal(new_loan.term_months) 

        for i in range(1, new_loan.term_months + 1):
            due_date = date.today() + relativedelta(months=i)
            installment = models.Installment(
                loan_id=new_loan.id,
                installment_number=i,
                due_date=due_date,
                amount=installment_amount
            )
            db.add(installment)
            
        # 7. Atualiza os Saldos das Contas
        lender_account.balance -= request.amount
        borrower_account.balance += request.amount

        # 8. Commita a Transação
        db.commit()

    # Trata exceções e garante o Rollback
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        # Embora a causa provável seja o erro de tipagem, mantemos a impressão
        # do erro para garantir que qualquer outro problema seja capturado.
        print(f"ERRO CRÍTICO NO ACEITAR OFERTA: {e}") 
        raise HTTPException(status_code=500, detail="Loan acceptance failed due to an unexpected server error.")
    
    db.refresh(new_loan)
    return new_loan