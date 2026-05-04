"""added Participant count field in meeting model

Revision ID: 8398bcfdf997
Revises: f239b103b31d
Create Date: 2026-04-29 12:59:16.932218

"""
from typing import Sequence, Union
from datetime import datetime

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8398bcfdf997'
down_revision: Union[str, Sequence[str], None] = 'f239b103b31d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Apply migration to upgrade database schema."""
    pass


def downgrade() -> None:
    """Apply migration to downgrade database schema."""
    pass
