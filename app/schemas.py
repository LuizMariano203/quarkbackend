from pydantic import BaseModel, EmailStr, Field
from decimal import Decimal
from typing import Optional, List
from datetime import date, datetime
# Importa todos os Enums atualizados, incluindo EntityType
from .models import (
    KYCStatus, AccountStatus, LoanStatus, InstallmentStatus, OfferStatus, 
    TransactionType, CreditSearchStatus, EntityType
)

# ----------------------------------------------------------------------
# SCHEMAS DE AUTENTICAÇÃO E USUÁRIO (EXPANDIDO)
# ----------------------------------------------------------------------
class UserBase(BaseModel):
    email: EmailStr
    nome_completo: str = Field(..., description="Nome Civil (PF) ou Razão Social (PJ)")
    tipo_entidade: EntityType
    # Campos opcionais conforme escopo
    nome_fantasia: Optional[str] = None
    cpf_cnpj_hash: Optional[str] = None
    data_fundacao_nasc: Optional[date] = None
    setor_atuacao: Optional[str] = None
    regiao: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserOut(UserBase):
    id: int
    kyc_status: KYCStatus
    score_credito: int
    data_cadastro: datetime

    class Config:
        orm_mode = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

# ----------------------------------------------------------------------
# SCHEMAS DE CARTEIRA E TRANSAÇÕES
# ----------------------------------------------------------------------
class AccountOut(BaseModel):
    balance: Decimal
    status: AccountStatus

    class Config:
        orm_mode = True

class TransactionOut(BaseModel):
    id: int
    timestamp_utc: datetime
    type: TransactionType
    value: Decimal
    origin_account_id: Optional[int]
    destination_account_id: Optional[int]
    reference_entity_id: Optional[str]

    class Config:
        orm_mode = True
        
class TransferRequest(BaseModel):
    destination_user_id: int
    amount: Decimal = Field(..., gt=0)

# ----------------------------------------------------------------------
# SCHEMAS DO MARKETPLACE (EXPANDIDO)
# ----------------------------------------------------------------------
class CreditOfferCreate(BaseModel):
    max_amount: Decimal = Field(..., gt=0)
    interest_rate: Decimal = Field(..., gt=0, lt=1)
    term_months: int = Field(..., gt=0)
    min_credit_score: int = Field(..., ge=0, le=1000)
    eligible_sector: Optional[str] = None
    data_expiracao: Optional[date] = None # ADICIONADO (escopo)

class CreditOfferOut(CreditOfferCreate):
    id: int
    lender_id: int
    status: OfferStatus

    class Config:
        orm_mode = True

class CreditSearchCreate(BaseModel):
    desired_amount: Decimal = Field(..., gt=0)
    max_interest_rate: Decimal = Field(..., gt=0, lt=1)
    desired_term_months: int = Field(..., gt=0)
    expiration_date: Optional[date] = None

class CreditSearchOut(CreditSearchCreate):
    id: int
    borrower_id: int
    status: CreditSearchStatus

    class Config:
        orm_mode = True

class AcceptOfferRequest(BaseModel):
    amount: Decimal = Field(..., gt=0)

# ----------------------------------------------------------------------
# SCHEMAS DE EMPRÉSTIMO E PARCELAS (EXPANDIDO)
# ----------------------------------------------------------------------
class InstallmentOut(BaseModel):
    installment_number: int
    due_date: date
    amount: Decimal
    status: InstallmentStatus
    valor_pago: Decimal # ADICIONADO (escopo)
    data_pagamento: Optional[datetime] # ADICIONADO (escopo)

    class Config:
        orm_mode = True

class LoanOut(BaseModel):
    id: int
    borrower_id: int
    lender_id: int
    amount: Decimal
    interest_rate: Decimal
    term_months: int
    status: LoanStatus
    # CAMPOS COMPLEMENTARES ADICIONADOS
    search_id_fk: Optional[int]
    data_contrato: date
    
    installments: List[InstallmentOut]

    class Config:
        orm_mode = True
        
class AdminSetBalanceRequest(BaseModel):
    user_id: int
    new_balance: Decimal = Field(..., ge=0)

class AdminUpdateKYCRequest(BaseModel):
    new_status: KYCStatus