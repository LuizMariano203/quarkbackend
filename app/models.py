# app/models.py (CORRIGIDO: Relações de Transaction movidas da classe User para Account)

from sqlalchemy import Column, Integer, String, DateTime, Enum as SQLAlchemyEnum, Numeric, ForeignKey, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .core.database import Base
import enum

class KYCStatus(str, enum.Enum): PENDING="PENDING"; VERIFIED="VERIFIED"; FAILED="FAILED"
class AccountStatus(str, enum.Enum): ACTIVE="ACTIVE"; BLOCKED="BLOCKED"
class LoanStatus(str, enum.Enum): ACTIVE="ACTIVE"; PAID="PAID"; DEFAULT="DEFAULT"
class InstallmentStatus(str, enum.Enum): PENDING="PENDING"; PAID="PAID"; OVERDUE="OVERDUE"; PARCIAL="PARCIAL"
class OfferStatus(str, enum.Enum): ACTIVE="ACTIVE"; PAUSED="PAUSADA"; COMMITTED="COMPROMETIDA"
class TransactionType(str, enum.Enum):
    P2P_DEBITO="P2P_DEBITO"
    P2P_CREDITO="P2P_CREDITO"
    EMPRESTIMO_CONCEDIDO="EMPRESTIMO_CONCEDIDO"
    PAGAMENTO_PARCELA="PAGAMENTO_PARCELA"
    DEPOSITO="DEPOSITO"
    SAQUE="SAQUE"

class CreditSearchStatus(str, enum.Enum): ACTIVE="ATIVA"; NEGOTIATING="NEGOCIANDO"; CANCELED="CANCELADA"


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    kyc_status = Column(SQLAlchemyEnum(KYCStatus), default=KYCStatus.PENDING, nullable=False)
    score_credito = Column(Integer, default=0, nullable=False)
    
    account = relationship("Account", back_populates="owner", uselist=False)
    # CORRIGIDO: Relações transactions_sent/received REMOVIDAS daqui.
    # Elas não pertencem à classe User.

class Account(Base):
    __tablename__ = "accounts"
    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    balance = Column(Numeric(15, 2), default=0.00, nullable=False)
    status = Column(SQLAlchemyEnum(AccountStatus), default=AccountStatus.ACTIVE, nullable=False)
    
    owner = relationship("User", back_populates="account")
    
    # CORRETO: As relações de Transaction PERMANECEM aqui, onde o FK existe.
    transactions_sent = relationship("Transaction", foreign_keys="[Transaction.origin_account_id]", back_populates="origin_account")
    transactions_received = relationship("Transaction", foreign_keys="[Transaction.destination_account_id]", back_populates="destination_account")

class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, index=True)
    timestamp_utc = Column(DateTime, default=func.now(), nullable=False)
    type = Column(SQLAlchemyEnum(TransactionType), nullable=False)
    value = Column(Numeric(15, 2), nullable=False)

    origin_account_id = Column(Integer, ForeignKey("accounts.id"))
    destination_account_id = Column(Integer, ForeignKey("accounts.id"))
    reference_entity_id = Column(String, index=True, nullable=True) 

    origin_account = relationship("Account", foreign_keys=[origin_account_id], back_populates="transactions_sent")
    destination_account = relationship("Account", foreign_keys=[destination_account_id], back_populates="transactions_received")

class CreditOffer(Base):
    __tablename__ = "credit_offers"
    id = Column(Integer, primary_key=True, index=True)
    lender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    max_amount = Column(Numeric(15, 2), nullable=False)
    interest_rate = Column(Numeric(5, 4), nullable=False)
    term_months = Column(Integer, nullable=False)
    min_credit_score = Column(Integer, default=0)
    status = Column(SQLAlchemyEnum(OfferStatus), default=OfferStatus.ACTIVE)
    eligible_sector = Column(String, nullable=True) 
    
class CreditSearch(Base): 
    __tablename__ = "credit_searches"
    id = Column(Integer, primary_key=True, index=True)
    borrower_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    desired_amount = Column(Numeric(15, 2), nullable=False)
    max_interest_rate = Column(Numeric(5, 4), nullable=False)
    desired_term_months = Column(Integer, nullable=False)
    
    status = Column(SQLAlchemyEnum(CreditSearchStatus), default=CreditSearchStatus.ACTIVE, nullable=False)
    expiration_date = Column(Date, nullable=True) 

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
    
    installments = relationship("Installment", back_populates="loan")

class Installment(Base):
    __tablename__ = "installments"
    id = Column(Integer, primary_key=True, index=True)
    loan_id = Column(Integer, ForeignKey("loans.id"), nullable=False)
    installment_number = Column(Integer, nullable=False)
    due_date = Column(Date, nullable=False)
    amount = Column(Numeric(15, 2), nullable=False)
    status = Column(SQLAlchemyEnum(InstallmentStatus), default=InstallmentStatus.PENDING)

    loan = relationship("Loan", back_populates="installments")