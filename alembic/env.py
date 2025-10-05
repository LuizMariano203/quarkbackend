import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# --- BLOCO ADICIONADO ---
# Adiciona o diretório raiz do projeto ao path do Python
sys.path.append(str(Path(__file__).resolve().parents[1]))

# Importa a Base dos seus modelos e as configurações
from app.core.database import Base
from app.core.config import settings
import app.models # Garante que os modelos sejam registrados no Base.metadata
# --- FIM DO BLOCO ADICIONADO ---

config = context.config

# Define a URL do banco de dados a partir das suas configurações
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# --- LINHA CRÍTICA DA CORREÇÃO ---
# Aponta para os metadados dos seus modelos SQLAlchemy.
target_metadata = Base.metadata
# --- FIM DA LINHA CRÍTICA ---


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()