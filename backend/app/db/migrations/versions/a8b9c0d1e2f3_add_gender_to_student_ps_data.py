"""add gender table and gender_id to student_ps_data

Revision ID: a8b9c0d1e2f3
Revises: f7a12de5c455
Create Date: 2026-03-17 12:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = 'a8b9c0d1e2f3'
down_revision: Union[str, None] = 'f7a12de5c455'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Gender jadvalini yaratish
    op.create_table(
        'gender',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(255), unique=True, nullable=False),
        sa.Column('key', sa.Integer(), unique=True, nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )

    # Default gender qiymatlarini kiritish
    op.execute("INSERT INTO gender (name, key, is_active) VALUES ('Noma''lum', 0, true)")
    op.execute("INSERT INTO gender (name, key, is_active) VALUES ('Erkak', 1, true)")
    op.execute("INSERT INTO gender (name, key, is_active) VALUES ('Ayol', 2, true)")

    # student_ps_data ga gender_id ustunini qo'shish
    op.add_column('student_ps_data', sa.Column('gender_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_student_ps_data_gender_id',
        'student_ps_data', 'gender',
        ['gender_id'], ['id'],
    )


def downgrade() -> None:
    op.drop_constraint('fk_student_ps_data_gender_id', 'student_ps_data', type_='foreignkey')
    op.drop_column('student_ps_data', 'gender_id')
    op.drop_table('gender')
