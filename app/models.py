# app/models.py (CORRIGIDO)

from sqlalchemy import Column, Integer, String, DateTime, Enum as SQLAlchemyEnum, Numeric, ForeignKey, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .core.database import Base
import enum

class KYCStatus(str, enum.Enum): PENDING="PENDING"; VERIFIED="VERIFIED"; FAILED="FAILED"
class AccountStatus(str, enum.Enum): ACTIVE="ACTIVE"; BLOCKED="BLOCKED"
class LoanStatus(str, enum.Enum): ACTIVE="ACTIVE"; PAID="PAID"; DEFAULT="DEFAULT"
class InstallmentStatus(str, enum.Enum): PENDING="PENDING"; PAID="PAID"; OVERDUE="OVERDUE"
class OfferStatus(str, enum.Enum): ACTIVE="ACTIVE"; PAUSED="PAUSED"; COMMITTED="COMMITTED"

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    kyc_status = Column(SQLAlchemyEnum(KYCStatus), default=KYCStatus.PENDING, nullable=False)
    
    # CORRIGIDO AQUI
    account = relationship("Account", back_populates="owner", uselist=False)

class Account(Base):
    __tablename__ = "accounts"
    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    balance = Column(Numeric(15, 2), default=0.00, nullable=False)
    status = Column(SQLAlchemyEnum(AccountStatus), default=AccountStatus.ACTIVE, nullable=False)
    
    # CORRIGIDO AQUI
    owner = relationship("User", back_populates="account")

class CreditOffer(Base):
    __tablename__ = "credit_offers"
    id = Column(Integer, primary_key=True, index=True)
    lender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    max_amount = Column(Numeric(15, 2), nullable=False)
    interest_rate = Column(Numeric(5, 4), nullable=False)
    term_months = Column(Integer, nullable=False)
    min_credit_score = Column(Integer, default=0)
    status = Column(SQLAlchemyEnum(OfferStatus), default=OfferStatus.ACTIVE)

class Loan(Base):
    __tablename__ = "loans"
    id = Column(Integer, primary_key=True, index=True)
    borrower_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    lender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    credit_offer_id = Column(Integer, ForeignKey("credit_offers.id"), nullable=False)
    amount = Column(Numeric(15, 2), nullable=False)
    interest_rate = Column(Numeric(5, 4), nullable=False)
    term_months = Column(Integer, nullable=False)
    status = Column(SQLAlchemyEnum(LoanStatus), default=LoanStatus.ACTIVE)
    
    # CORRIGIDO AQUI
    installments = relationship("Installment", back_populates="loan")

class Installment(Base):
    __tablename__ = "installments"
    id = Column(Integer, primary_key=True, index=True)
    loan_id = Column(Integer, ForeignKey("loans.id"), nullable=False)
    installment_number = Column(Integer, nullable=False)
    due_date = Column(Date, nullable=False)
    amount = Column(Numeric(15, 2), nullable=False)
    status = Column(SQLAlchemyEnum(InstallmentStatus), default=InstallmentStatus.PENDING)

    # CORRIGIDO AQUI
    loan = relationship("Loan", back_populates="installments")