"""added Participant count field in meeting model

Revision ID: f239b103b31d
Revises: 278589bc3de5
Create Date: 2026-04-29 12:52:47.339278

"""
from typing import Sequence, Union
from datetime import datetime

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f239b103b31d'
down_revision: Union[str, Sequence[str], None] = '278589bc3de5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Apply migration to upgrade database schema."""
    pass


def downgrade() -> None:
    """Apply migration to downgrade database schema."""
    pass
