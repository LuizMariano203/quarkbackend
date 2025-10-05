from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql # Importado para trabalhar com tipos Postgresql
from sqlalchemy.sql import text # Importado para comandos SQL brutos, se necessário

# revision identifiers, used by Alembic.
revision: str = '3527449eba98'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# ----------------------------------------------------------------------
# 0. DEFINIÇÃO DOS TIPOS ENUM FORA DA FUNÇÃO
# ----------------------------------------------------------------------
ENTITY_TYPE = postgresql.ENUM('PF', 'PJ', name='entitytype', create_type=False)
KYC_STATUS = postgresql.ENUM('PENDING', 'VERIFIED', 'FAILED', name='kycstatus', create_type=False)
ACCOUNT_STATUS = postgresql.ENUM('ACTIVE', 'BLOCKED', name='accountstatus', create_type=False)
OFFER_STATUS = postgresql.ENUM('ACTIVE', 'PAUSED', 'COMMITTED', name='offerstatus', create_type=False)
LOAN_STATUS = postgresql.ENUM('ACTIVE', 'PAID', 'DEFAULT', name='loanstatus', create_type=False)
INSTALLMENT_STATUS = postgresql.ENUM('PENDING', 'PAID', 'OVERDUE', 'PARCIAL', name='installmentstatus', create_type=False)
TRANSACTION_TYPE = postgresql.ENUM('P2P_DEBITO', 'P2P_CREDITO', 'EMPRESTIMO_CONCEDIDO', 'PAGAMENTO_PARCELA', 'DEPOSITO', 'SAQUE', name='transactiontype', create_type=False)
CREDIT_SEARCH_STATUS = postgresql.ENUM('ACTIVE', 'NEGOTIATING', 'CANCELED', name='creditsearchstatus', create_type=False)


def upgrade() -> None:
    """Upgrade schema."""
    
    bind = op.get_bind()
    
    # 1. CRIAÇÃO EXPLÍCITA DE TODOS OS TIPOS ENUM NO POSTGRESQL (RESOLVE UNDEFINEDOBJECT)
    KYC_STATUS.create(bind, checkfirst=True)
    ACCOUNT_STATUS.create(bind, checkfirst=True)
    OFFER_STATUS.create(bind, checkfirst=True)
    LOAN_STATUS.create(bind, checkfirst=True)
    INSTALLMENT_STATUS.create(bind, checkfirst=True)
    TRANSACTION_TYPE.create(bind, checkfirst=True)
    CREDIT_SEARCH_STATUS.create(bind, checkfirst=True)
    ENTITY_TYPE.create(bind, checkfirst=True) # Este é o tipo que estava falhando!

    # 2. CRIAÇÃO DE TABELAS (Corrigida para usar os objetos ENUM criados)
    
    op.create_table('users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('email', sa.String(), nullable=False),
    sa.Column('hashed_password', sa.String(), nullable=False),
    # USANDO O OBJETO ENUM
    sa.Column('tipo_entidade', ENTITY_TYPE, nullable=False),
    sa.Column('nome_completo', sa.String(), nullable=False),
    sa.Column('nome_fantasia', sa.String(), nullable=True),
    sa.Column('cpf_cnpj_hash', sa.String(), nullable=True),
    sa.Column('data_fundacao_nasc', sa.Date(), nullable=True),
    # Adicionado server_default para data_cadastro que é NOT NULL
    sa.Column('data_cadastro', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('score_credito', sa.Integer(), nullable=False),
    sa.Column('setor_atuacao', sa.String(), nullable=True),
    sa.Column('regiao', sa.String(), nullable=True),
    sa.Column('kyc_status', KYC_STATUS, nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    
    op.create_table('accounts',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('owner_id', sa.Integer(), nullable=False),
    sa.Column('balance', sa.Numeric(precision=15, scale=2), nullable=False),
    sa.Column('status', ACCOUNT_STATUS, nullable=False),
    sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_accounts_id'), 'accounts', ['id'], unique=False)
    
    op.create_table('credit_offers',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('lender_id', sa.Integer(), nullable=False),
    sa.Column('max_amount', sa.Numeric(precision=15, scale=2), nullable=False),
    sa.Column('interest_rate', sa.Numeric(precision=5, scale=4), nullable=False),
    sa.Column('term_months', sa.Integer(), nullable=False),
    sa.Column('min_credit_score', sa.Integer(), nullable=True),
    sa.Column('status', OFFER_STATUS, nullable=True),
    sa.Column('eligible_sector', sa.String(), nullable=True),
    sa.Column('data_expiracao', sa.Date(), nullable=True),
    sa.ForeignKeyConstraint(['lender_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_credit_offers_id'), 'credit_offers', ['id'], unique=False)
    
    op.create_table('credit_searches',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('borrower_id', sa.Integer(), nullable=False),
    sa.Column('desired_amount', sa.Numeric(precision=15, scale=2), nullable=False),
    sa.Column('max_interest_rate', sa.Numeric(precision=5, scale=4), nullable=False),
    sa.Column('desired_term_months', sa.Integer(), nullable=False),
    sa.Column('status', CREDIT_SEARCH_STATUS, nullable=False),
    sa.Column('expiration_date', sa.Date(), nullable=True),
    sa.ForeignKeyConstraint(['borrower_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_credit_searches_id'), 'credit_searches', ['id'], unique=False)
    
    op.create_table('loans',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('borrower_id', sa.Integer(), nullable=False),
    sa.Column('lender_id', sa.Integer(), nullable=False),
    sa.Column('credit_offer_id', sa.Integer(), nullable=False),
    sa.Column('search_id_fk', sa.Integer(), nullable=True),
    sa.Column('amount', sa.Numeric(precision=15, scale=2), nullable=False),
    sa.Column('interest_rate', sa.Numeric(precision=5, scale=4), nullable=False),
    sa.Column('term_months', sa.Integer(), nullable=False),
    sa.Column('data_contrato', sa.Date(), nullable=False),
    sa.Column('status', LOAN_STATUS, nullable=True),
    sa.ForeignKeyConstraint(['borrower_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['credit_offer_id'], ['credit_offers.id'], ),
    sa.ForeignKeyConstraint(['lender_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['search_id_fk'], ['credit_searches.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_loans_id'), 'loans', ['id'], unique=False)
    
    op.create_table('transactions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('timestamp_utc', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('type', TRANSACTION_TYPE, nullable=False),
    sa.Column('value', sa.Numeric(precision=15, scale=2), nullable=False),
    sa.Column('origin_account_id', sa.Integer(), nullable=True),
    sa.Column('destination_account_id', sa.Integer(), nullable=True),
    sa.Column('reference_entity_id', sa.String(), nullable=True),
    sa.ForeignKeyConstraint(['destination_account_id'], ['accounts.id'], ),
    sa.ForeignKeyConstraint(['origin_account_id'], ['accounts.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_transactions_id'), 'transactions', ['id'], unique=False)
    op.create_index(op.f('ix_transactions_reference_entity_id'), 'transactions', ['reference_entity_id'], unique=False)
    
    op.create_table('installments',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('loan_id', sa.Integer(), nullable=False),
    sa.Column('installment_number', sa.Integer(), nullable=False),
    sa.Column('due_date', sa.Date(), nullable=False),
    sa.Column('amount', sa.Numeric(precision=15, scale=2), nullable=False),
    sa.Column('status', INSTALLMENT_STATUS, nullable=True),
    sa.Column('valor_pago', sa.Numeric(precision=15, scale=2), nullable=False),
    sa.Column('data_pagamento', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['loan_id'], ['loans.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_installments_id'), 'installments', ['id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    
    op.drop_index(op.f('ix_installments_id'), table_name='installments')
    op.drop_table('installments')
    
    op.drop_index(op.f('ix_transactions_reference_entity_id'), table_name='transactions')
    op.drop_index(op.f('ix_transactions_id'), table_name='transactions')
    op.drop_table('transactions')
    
    op.drop_index(op.f('ix_loans_id'), table_name='loans')
    op.drop_table('loans')
    
    op.drop_index(op.f('ix_credit_searches_id'), table_name='credit_searches')
    op.drop_table('credit_searches')
    
    op.drop_index(op.f('ix_credit_offers_id'), table_name='credit_offers')
    op.drop_table('credit_offers')
    
    op.drop_index(op.f('ix_accounts_id'), table_name='accounts')
    op.drop_table('accounts')
    
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
    
    # CRÍTICO: REMOÇÃO EXPLÍCITA DE TODOS OS TIPOS ENUM
    bind = op.get_bind()
    INSTALLMENT_STATUS.drop(bind, checkfirst=True)
    LOAN_STATUS.drop(bind, checkfirst=True)
    OFFER_STATUS.drop(bind, checkfirst=True)
    ACCOUNT_STATUS.drop(bind, checkfirst=True)
    KYC_STATUS.drop(bind, checkfirst=True)
    TRANSACTION_TYPE.drop(bind, checkfirst=True)
    CREDIT_SEARCH_STATUS.drop(bind, checkfirst=True)
    ENTITY_TYPE.drop(bind, checkfirst=True)