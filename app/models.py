# app/models.py (CORRIGIDO E COMPLEMENTADO)

from sqlalchemy import Column, Integer, String, DateTime, Enum as SQLAlchemyEnum, Numeric, ForeignKey, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .core.database import Base
import enum
from datetime import date # Importado date para default em Loan


# ENUMS COMPLEMENTARES
class EntityType(str, enum.Enum): PF="PF"; PJ="PJ" # NOVO ENUM: Tipo de Entidade (PF ou PJ) [cite: 23]
class KYCStatus(str, enum.Enum): PENDING="PENDING"; VERIFIED="VERIFIED"; FAILED="FAILED" # [cite: 37]
class AccountStatus(str, enum.Enum): ACTIVE="ACTIVE"; BLOCKED="BLOCKED" # [cite: 44]
class LoanStatus(str, enum.Enum): ACTIVE="ATIVO"; PAID="PAGO"; DEFAULT="DEFAULT" # [cite: 86]
class OfferStatus(str, enum.Enum): ACTIVE="ACTIVE"; PAUSED="PAUSADA"; COMMITTED="COMPROMETIDA" # [cite: 66]
class CreditSearchStatus(str, enum.Enum): ACTIVE="ATIVA"; NEGOTIATING="NEGOCIANDO"; CANCELED="CANCELADA" # [cite: 75]
class InstallmentStatus(str, enum.Enum): PENDING="PENDENTE"; PAID="PAGO"; OVERDUE="ATRASO"; PARCIAL="PARCIAL" # [cite: 95]
class TransactionType(str, enum.Enum):
    P2P_DEBITO="P2P_DEBITO"
    P2P_CREDITO="P2P_CREDITO"
    EMPRESTIMO_CONCEDIDO="EMPRESTIMO_CONCEDIDO"
    PAGAMENTO_PARCELA="PAGAMENTO_PARCELA"
    DEPOSITO="DEPOSITO"
    SAQUE="SAQUE"


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    
    # ATRIBUTOS COMPLEMENTARES ADICIONADOS [cite: 23-37]
    tipo_entidade = Column(SQLAlchemyEnum(EntityType), nullable=False)
    nome_completo = Column(String, nullable=False)
    nome_fantasia = Column(String, nullable=True) # [cite: 25]
    cpf_cnpj_hash = Column(String, nullable=True) # Usado hash, nullable para evitar erro na migração inicial
    data_fundacao_nasc = Column(Date, nullable=True) # [cite: 31]
    data_cadastro = Column(DateTime, default=func.now(), nullable=False) # [cite: 32]
    score_credito = Column(Integer, default=0, nullable=False) # [cite: 33]
    setor_atuacao = Column(String, nullable=True) # [cite: 34]
    regiao = Column(String, nullable=True) # [cite: 36]
    kyc_status = Column(SQLAlchemyEnum(KYCStatus), default=KYCStatus.PENDING, nullable=False)
    
    account = relationship("Account", back_populates="owner", uselist=False)
    # Relações de Transaction removidas do User e mantidas na Account

class Account(Base):
    __tablename__ = "accounts"
    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    balance = Column(Numeric(15, 2), default=0.00, nullable=False)
    status = Column(SQLAlchemyEnum(AccountStatus), default=AccountStatus.ACTIVE, nullable=False)
    
    owner = relationship("User", back_populates="account")
    transactions_sent = relationship("Transaction", foreign_keys="[Transaction.origin_account_id]", back_populates="origin_account")
    transactions_received = relationship("Transaction", foreign_keys="[Transaction.destination_account_id]", back_populates="destination_account")

class Transaction(Base):
    __tablename__ = "transactions"
    # Adicionada referência de entidade conforme escopo [cite: 53]
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
    # ATRIBUTOS COMPLEMENTARES ADICIONADOS [cite: 64-65]
    eligible_sector = Column(String, nullable=True) 
    data_expiracao = Column(Date, nullable=True) 
    
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
    
    # ATRIBUTOS COMPLEMENTARES ADICIONADOS [cite: 79-85]
    search_id_fk = Column(Integer, ForeignKey("credit_searches.id"), nullable=True)
    amount = Column(Numeric(15, 2), nullable=False) # valor_concedido [cite: 83]
    interest_rate = Column(Numeric(5, 4), nullable=False) # juros_acordado [cite: 84]
    term_months = Column(Integer, nullable=False)
    data_contrato = Column(Date, default=date.today(), nullable=False) # [cite: 85]
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
    
    # ATRIBUTOS COMPLEMENTARES ADICIONADOS [cite: 93-94]
    valor_pago = Column(Numeric(15, 2), default=0.00, nullable=False) 
    data_pagamento = Column(DateTime, nullable=True)

    loan = relationship("Loan", back_populates="installments")