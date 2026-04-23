"""Uchta head'ni birlashtirish (5d334063d56d, a1f3c7b29e04, f59319a19404).

Bu bo'sh merge migration — DB schema o'zgartirmaydi.
Alembic'ga head'lar chiziqli tarixga birlashishini ko'rsatadi.

Revision ID: m1h0234d8e2
Revises: 5d334063d56d, a1f3c7b29e04, f59319a19404
Create Date: 2026-04-17 12:05:00.000000
"""
from typing import Sequence, Union


revision: str = "m1h0234d8e2"
down_revision: Union[str, Sequence[str], None] = (
    "5d334063d56d",
    "a1f3c7b29e04",
    "f59319a19404",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
