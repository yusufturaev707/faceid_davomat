"""merge multiple heads

Revision ID: da0f5e1b0121
Revises: 5d334063d56d, f59319a19404
Create Date: 2026-04-13 13:36:02.622167
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'da0f5e1b0121'
down_revision: Union[str, None] = ('5d334063d56d', 'f59319a19404')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
