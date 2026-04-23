"""make student_logs.student_id unique (one log per student)

Revision ID: b8e4f2a91c37
Revises: a7c9f3d2e1b4
Create Date: 2026-04-13 15:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b8e4f2a91c37"
down_revision: Union[str, None] = "a7c9f3d2e1b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1) Dedupe: har bir student_id uchun eng kichik id li yozuvni saqlab,
    #    qolgan duplicatelarni o'chiramiz.
    op.execute(
        """
        DELETE FROM student_logs sl
        USING student_logs sl2
        WHERE sl.student_id = sl2.student_id
          AND sl.id > sl2.id
        """
    )

    # 2) Unique constraint + index
    op.create_unique_constraint(
        "uq_student_logs_student_id", "student_logs", ["student_id"]
    )
    op.create_index(
        "ix_student_logs_student_id", "student_logs", ["student_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_student_logs_student_id", table_name="student_logs")
    op.drop_constraint(
        "uq_student_logs_student_id", "student_logs", type_="unique"
    )
