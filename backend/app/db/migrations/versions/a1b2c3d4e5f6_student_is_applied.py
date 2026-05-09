"""student is_applied and desc_apply

Revision ID: a1b2c3d4e5f6
Revises: 70f1aecd3287
Create Date: 2026-05-09 10:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '70f1aecd3287'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Ustun NOT NULL bo'lgani uchun server_default=FALSE qoldiriladi —
    # tashqi API yuklash kabi yo'llardan kelgan INSERT'larda bu maydon
    # ko'rsatilmasa, Postgres avtomatik FALSE qiymatini ishlatadi.
    op.add_column(
        'students',
        sa.Column(
            'is_applied',
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        'students',
        sa.Column('desc_apply', sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('students', 'desc_apply')
    op.drop_column('students', 'is_applied')
