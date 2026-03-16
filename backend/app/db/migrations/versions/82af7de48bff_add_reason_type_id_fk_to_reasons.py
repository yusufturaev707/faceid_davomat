"""add reason_type_id fk to reasons

Revision ID: 82af7de48bff
Revises: 5a684258487e
Create Date: 2026-03-16 10:35:37.161277
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '82af7de48bff'
down_revision: Union[str, None] = '5a684258487e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # reason_types jadvali allaqachon mavjud (oldingi migratsiyada yaratilgan)
    # Faqat reasons jadvaliga reason_type_id FK qo'shish (nullable)
    op.add_column('reasons', sa.Column('reason_type_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_reasons_reason_type_id'), 'reasons', ['reason_type_id'], unique=False)
    op.create_foreign_key('fk_reasons_reason_type_id', 'reasons', 'reason_types', ['reason_type_id'], ['id'])


def downgrade() -> None:
    op.drop_constraint('fk_reasons_reason_type_id', 'reasons', type_='foreignkey')
    op.drop_index(op.f('ix_reasons_reason_type_id'), table_name='reasons')
    op.drop_column('reasons', 'reason_type_id')
