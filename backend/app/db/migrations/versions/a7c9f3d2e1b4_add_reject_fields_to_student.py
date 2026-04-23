"""add reject_reason_id and rejected_at to students

Revision ID: a7c9f3d2e1b4
Revises: da0f5e1b0121
Create Date: 2026-04-13 14:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a7c9f3d2e1b4'
down_revision: Union[str, None] = 'da0f5e1b0121'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "students",
        sa.Column("reject_reason_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "students",
        sa.Column("rejected_at", sa.DateTime(), nullable=True),
    )
    op.create_index(
        "ix_students_reject_reason_id",
        "students",
        ["reject_reason_id"],
    )
    op.create_foreign_key(
        "fk_students_reject_reason_id_reasons",
        "students",
        "reasons",
        ["reject_reason_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_students_reject_reason_id_reasons", "students", type_="foreignkey"
    )
    op.drop_index("ix_students_reject_reason_id", table_name="students")
    op.drop_column("students", "rejected_at")
    op.drop_column("students", "reject_reason_id")
