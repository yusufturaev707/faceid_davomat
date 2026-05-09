"""student.is_applied: re-add server_default=FALSE

Oldingi migration (a1b2c3d4e5f6) server_default'ni backfill'dan keyin
o'chirgan edi. Bu tashqi API'dan student yuklayotganda (yoki ORM dan
boshqa yo'l bilan kelgan INSERT'larda) NOT NULL violation chiqaradi,
chunki ba'zi yo'llarda Python-tomonida `default=False` qo'llanmaydi.

Tuzatma: ustunda doimiy `server_default=FALSE` saqlanadi.

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-05-09 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        'students',
        'is_applied',
        server_default=sa.false(),
        existing_type=sa.Boolean(),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        'students',
        'is_applied',
        server_default=None,
        existing_type=sa.Boolean(),
        existing_nullable=False,
    )
