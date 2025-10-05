from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import date
from dateutil.relativedelta import relativedelta
from decimal import Decimal
from typing import List
from sqlalchemy import or_ 
from sqlalchemy.sql import func 

from ... import models, schemas
from ...core import database, security

router = APIRouter()

@router.post(
    "/offers/{offer_id}/accept", 
    response_model=schemas.LoanOut, 
    status_code=status.HTTP_201_CREATED,
    summary="Aceitar Oferta de Crédito",
    description="Permite que um usuário verificado aceite uma oferta de crédito ativa, bloqueando fundos na conta do credor e criando um novo empréstimo e as parcelas correspondentes."
)
def accept_offer(
    offer_id: int,
    request: schemas.AcceptOfferRequest,
    borrower: models.User = Depends(security.get_current_user),
    db: Session = Depends(database.get_db)
):
    if borrower.kyc_status != models.KYCStatus.VERIFIED:
        raise HTTPException(status_code=403, detail="User must be KYC verified to accept offers")

    try:
        # 1. Busca e Bloqueio da Oferta
        offer = db.query(models.CreditOffer).filter(models.CreditOffer.id == offer_id).with_for_update().first()
        if not offer or offer.status != models.OfferStatus.ACTIVE:
            raise HTTPException(status_code=404, detail="Offer not found or not active")
        
        # ... (Restante das validações de valor/propriedade)
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
            borrower_id=borrower.id, lender_id=offer.lender_id, credit_offer_id=offer.id,
            amount=request.amount, interest_rate=offer.interest_rate, term_months=offer.term_months,
            # Novos campos
            search_id_fk=None, # Não recebemos search_id aqui, mas o campo está mapeado
            data_contrato=date.today()
        )
        db.add(new_loan)
        db.flush()

        # 6. Calcula e Cria as Parcelas (Installments)
        term_factor = Decimal(new_loan.term_months) / Decimal(12)
        total_interest = new_loan.amount * new_loan.interest_rate * term_factor
        total_repayment = new_loan.amount + total_interest
        installment_amount = total_repayment / Decimal(new_loan.term_months) 

        for i in range(1, new_loan.term_months + 1):
            due_date = date.today() + relativedelta(months=i)
            installment = models.Installment(
                loan_id=new_loan.id, installment_number=i, due_date=due_date, 
                amount=installment_amount
                # valor_pago/data_pagamento usam defaults no modelo
            )
            db.add(installment)
            
        # 7. Atualiza os Saldos das Contas (Saída do Credor, Entrada do Mutuário)
        lender_account.balance -= request.amount
        borrower_account.balance += request.amount

        # 8. Cria Registros de Transação (Ledger)
        loan_reference = str(new_loan.id)
        db.add(models.Transaction(
            type=models.TransactionType.EMPRESTIMO_CONCEDIDO, value=request.amount,
            origin_account_id=lender_account.id, destination_account_id=borrower_account.id,
            reference_entity_id=loan_reference
        ))
        db.add(models.Transaction(
            type=models.TransactionType.P2P_CREDITO, value=request.amount,
            origin_account_id=lender_account.id, destination_account_id=borrower_account.id,
            reference_entity_id=loan_reference
        ))

        db.commit()

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        print(f"ERRO CRÍTICO NO ACEITAR OFERTA: {e}") 
        raise HTTPException(status_code=500, detail="Loan acceptance failed due to an unexpected server error.")
    
    db.refresh(new_loan)
    return new_loan

@router.get(
    "/loan/my-loans", 
    response_model=List[schemas.LoanOut],
    summary="Listar Meus Empréstimos",
    description="Retorna todos os contratos de empréstimo onde o usuário autenticado é o Mutuário (Borrower) ou o Credor (Lender)."
)
def get_my_loans(
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(database.get_db)
):
    user_id = current_user.id
    
    loans = db.query(models.Loan).filter(
        or_(
            models.Loan.borrower_id == user_id,
            models.Loan.lender_id == user_id
        )
    ).all()
    
    return loans

@router.get(
    "/loan/{loan_id}/installments", 
    response_model=List[schemas.InstallmentOut],
    summary="Detalhar Parcelas do Empréstimo",
    description="Retorna a lista de parcelas (cronograma de pagamento) para um empréstimo específico, visível apenas para o Mutuário ou Credor."
)
def get_loan_installments(
    loan_id: int,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(database.get_db)
):
    # 1. Verifica se o usuário tem acesso ao empréstimo
    loan = db.query(models.Loan).filter(models.Loan.id == loan_id).first()
    
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found.")
        
    user_id = current_user.id
    
    # Validação de Autorização: Apenas o mutuário ou o credor podem ver as parcelas
    if loan.borrower_id != user_id and loan.lender_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to view these installments.")
        
    # 2. Busca as parcelas
    installments = db.query(models.Installment).filter(
        models.Installment.loan_id == loan_id
    ).order_by(models.Installment.installment_number).all()
    
    return installments

@router.post(
    "/loan/{loan_id}/pay-installment", 
    status_code=status.HTTP_200_OK,
    summary="Processar Pagamento de Parcela",
    description="Permite que o Mutuário pague a próxima parcela PENDENTE de um empréstimo específico. Realiza o débito na conta do Mutuário e o crédito na conta do Credor."
)
def pay_installment(
    loan_id: int,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(database.get_db)
):
    # 1. Recupera o empréstimo
    loan = db.query(models.Loan).filter(models.Loan.id == loan_id).first()
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found.")
        
    # 2. Valida Autorização (Apenas o Mutuário pode pagar)
    if loan.borrower_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the borrower is authorized to pay this loan installment.")

    # 3. Identifica a próxima parcela PENDENTE (ordenada pelo número da parcela)
    next_installment = db.query(models.Installment).filter(
        models.Installment.loan_id == loan_id,
        models.Installment.status == models.InstallmentStatus.PENDING
    ).order_by(models.Installment.installment_number).first()
    
    if not next_installment:
        raise HTTPException(status_code=400, detail="No pending installments found, or loan is fully paid.")

    # Início do Bloco Transacional para Débito/Crédito
    try:
        # 4. Bloqueia e verifica a conta do Mutuário
        borrower_account = db.query(models.Account).filter(models.Account.owner_id == loan.borrower_id).with_for_update().first()
        lender_account = db.query(models.Account).filter(models.Account.owner_id == loan.lender_id).with_for_update().first()

        payment_amount = next_installment.amount
        
        if borrower_account.balance < payment_amount:
            raise HTTPException(status_code=400, detail=f"Insufficient funds. Required: R$ {payment_amount}")

        # 5. Executa a Transação (Débito e Crédito)
        borrower_account.balance -= payment_amount
        lender_account.balance += payment_amount

        # 6. Atualiza o Status da Parcela (Utilizando novos campos)
        next_installment.status = models.InstallmentStatus.PAID
        next_installment.valor_pago = payment_amount
        next_installment.data_pagamento = func.now() # Utiliza func.now() para definir a data/hora atual

        # 7. Cria Registro de Transação (Ledger)
        installment_reference = str(next_installment.id)
        
        db.add(models.Transaction(
            type=models.TransactionType.PAGAMENTO_PARCELA, value=payment_amount,
            origin_account_id=borrower_account.id, destination_account_id=lender_account.id,
            reference_entity_id=installment_reference
        ))

        # 8. Verifica se o empréstimo foi totalmente pago
        # Contamos as parcelas PENDENTES. Se a contagem for 0, o empréstimo está PAGO.
        remaining_installments = db.query(models.Installment).filter(
            models.Installment.loan_id == loan_id,
            models.Installment.status == models.InstallmentStatus.PENDING
        ).count()
        
        if remaining_installments == 0:
            loan.status = models.LoanStatus.PAID

        db.commit()

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        print(f"ERRO CRÍTICO NO PAGAMENTO DE PARCELA: {e}")
        raise HTTPException(status_code=500, detail="Payment failed due to an unexpected server error.")
    
    return {"message": f"Installment {next_installment.installment_number} paid successfully."}