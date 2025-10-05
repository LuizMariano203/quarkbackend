"""empty message

Revision ID: 6c93c7b01c14
Revises: b79a3a103705
Create Date: 2025-10-05 00:51:27.489299

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6c93c7b01c14'
down_revision: Union[str, Sequence[str], None] = 'b79a3a103705'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
