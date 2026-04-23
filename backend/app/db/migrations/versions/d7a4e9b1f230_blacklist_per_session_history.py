"""student_blacklist: per-session history (session_smena_id + created_at)

Revision ID: d7a4e9b1f230
Revises: c9f3a1b5d820
Create Date: 2026-04-14 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d7a4e9b1f230"
down_revision: Union[str, None] = "c9f3a1b5d820"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "student_blacklist",
        sa.Column("session_smena_id", sa.Integer(), nullable=True),
    )
    op.create_index(
        "ix_student_blacklist_session_smena_id",
        "student_blacklist",
        ["session_smena_id"],
    )
    op.create_foreign_key(
        "fk_student_blacklist_session_smena",
        "student_blacklist",
        "test_session_smena",
        ["session_smena_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_student_blacklist_session_smena",
        "student_blacklist",
        type_="foreignkey",
    )
    op.drop_index(
        "ix_student_blacklist_session_smena_id", table_name="student_blacklist"
    )
    op.drop_column("student_blacklist", "session_smena_id")
