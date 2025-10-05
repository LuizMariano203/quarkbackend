from pydantic import BaseModel, EmailStr, Field
from decimal import Decimal
from typing import Optional, List
from datetime import date
from .models import KYCStatus, AccountStatus, LoanStatus, InstallmentStatus, OfferStatus

class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: int
    email: EmailStr
    kyc_status: KYCStatus

    class Config:
        orm_mode = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

class AccountOut(BaseModel):
    balance: Decimal
    status: AccountStatus

    class Config:
        orm_mode = True

class TransferRequest(BaseModel):
    destination_user_id: int
    amount: Decimal = Field(..., gt=0)

class CreditOfferCreate(BaseModel):
    max_amount: Decimal = Field(..., gt=0)
    interest_rate: Decimal = Field(..., gt=0, lt=1)
    term_months: int = Field(..., gt=0)
    min_credit_score: int = Field(..., ge=0, le=1000)

class CreditOfferOut(CreditOfferCreate):
    id: int
    lender_id: int
    status: OfferStatus

    class Config:
        orm_mode = True

class AcceptOfferRequest(BaseModel):
    amount: Decimal = Field(..., gt=0)

class InstallmentOut(BaseModel):
    installment_number: int
    due_date: date
    amount: Decimal
    status: InstallmentStatus

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
    installments: List[InstallmentOut]

    class Config:
        orm_mode = True
        
class AdminSetBalanceRequest(BaseModel):
    user_id: int
    new_balance: Decimal = Field(..., ge=0)

class AdminUpdateKYCRequest(BaseModel):
    new_status: KYCStatus