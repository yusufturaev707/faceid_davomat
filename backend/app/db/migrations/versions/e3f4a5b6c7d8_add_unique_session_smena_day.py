"""add unique constraint on test_session_smena (session, smena, day)

Revision ID: e3f4a5b6c7d8
Revises: 788bdbd52ccf
Create Date: 2026-03-16 16:00:00.000000
"""
from typing import Sequence, Union

from alembic import op


revision: str = 'e3f4a5b6c7d8'
down_revision: Union[str, None] = '788bdbd52ccf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # number ustunidagi noto'g'ri unique constraintni olib tashlash
    op.drop_constraint('test_session_smena_number_key', 'test_session_smena', type_='unique')
    # (session, smena, day) bo'yicha to'g'ri unique constraint qo'shish
    op.create_unique_constraint(
        'uq_session_smena_day',
        'test_session_smena',
        ['test_session_id', 'test_smena_id', 'day'],
    )


def downgrade() -> None:
    op.drop_constraint('uq_session_smena_day', 'test_session_smena', type_='unique')
    op.create_unique_constraint('test_session_smena_number_key', 'test_session_smena', ['number'])
