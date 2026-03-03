"""add image_path to verification_logs

Revision ID: a3b7c9d1e2f4
Revises: e24f5bf76836
Create Date: 2026-03-03 18:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3b7c9d1e2f4'
down_revision: Union[str, None] = 'e24f5bf76836'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('verification_logs', sa.Column('image_path', sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column('verification_logs', 'image_path')
