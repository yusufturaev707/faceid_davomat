"""api_keys.key_hash String(64) -> String(128) uchun HMAC versiya prefiksi

Revision ID: a1f3c7b29e04
Revises: e8b5c2a41f90
Create Date: 2026-04-17 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1f3c7b29e04"
down_revision: Union[str, None] = "e8b5c2a41f90"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "api_keys",
        "key_hash",
        existing_type=sa.String(length=64),
        type_=sa.String(length=128),
        existing_nullable=False,
    )


def downgrade() -> None:
    # Ogohlantirish: agar v2 hashlar mavjud bo'lsa, ular kesiladi.
    op.alter_column(
        "api_keys",
        "key_hash",
        existing_type=sa.String(length=128),
        type_=sa.String(length=64),
        existing_nullable=False,
    )
