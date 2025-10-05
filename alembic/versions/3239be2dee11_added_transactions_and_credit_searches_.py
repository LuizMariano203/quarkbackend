"""Added transactions and credit searches tables

Revision ID: 3239be2dee11
Revises: 6c93c7b01c14
Create Date: 2025-10-05 00:59:03.139132

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3239be2dee11'
down_revision: Union[str, Sequence[str], None] = '6c93c7b01c14'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
