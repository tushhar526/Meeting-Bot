"""added Participant count field in meeting model

Revision ID: 278589bc3de5
Revises: 2e0eeb8393c3
Create Date: 2026-04-29 12:51:57.086359

"""
from typing import Sequence, Union
from datetime import datetime

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '278589bc3de5'
down_revision: Union[str, Sequence[str], None] = '2e0eeb8393c3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Apply migration to upgrade database schema."""
    pass


def downgrade() -> None:
    """Apply migration to downgrade database schema."""
    pass
