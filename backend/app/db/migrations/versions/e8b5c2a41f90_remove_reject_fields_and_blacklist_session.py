"""Remove Student.reject_reason_id/rejected_at + StudentBlacklist.session_smena_id

Revision ID: e8b5c2a41f90
Revises: d7a4e9b1f230
Create Date: 2026-04-14 18:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e8b5c2a41f90"
down_revision: Union[str, None] = "d7a4e9b1f230"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # students.reject_reason_id + rejected_at
    # FK va index nomlari avvalgi migration bo'yicha aniq emas; drop_constraint
    # PostgreSQL'da FK nomini avtomatik (name-based) topadi, lekin ishonch uchun
    # pg_constraint orqali dinamik drop qilamiz.
    op.execute(
        """
        DO $$
        DECLARE
            c RECORD;
        BEGIN
            FOR c IN
                SELECT conname FROM pg_constraint
                WHERE conrelid = 'students'::regclass
                  AND contype = 'f'
                  AND conname ILIKE '%reject_reason%'
            LOOP
                EXECUTE 'ALTER TABLE students DROP CONSTRAINT ' || quote_ident(c.conname);
            END LOOP;
        END $$;
        """
    )
    op.execute("DROP INDEX IF EXISTS ix_students_reject_reason_id")
    op.drop_column("students", "reject_reason_id")
    op.drop_column("students", "rejected_at")

    # student_blacklist.session_smena_id
    op.execute(
        """
        DO $$
        DECLARE
            c RECORD;
        BEGIN
            FOR c IN
                SELECT conname FROM pg_constraint
                WHERE conrelid = 'student_blacklist'::regclass
                  AND contype = 'f'
                  AND conname ILIKE '%session_smena%'
            LOOP
                EXECUTE 'ALTER TABLE student_blacklist DROP CONSTRAINT ' || quote_ident(c.conname);
            END LOOP;
        END $$;
        """
    )
    op.execute("DROP INDEX IF EXISTS ix_student_blacklist_session_smena_id")
    op.drop_column("student_blacklist", "session_smena_id")


def downgrade() -> None:
    # students
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

    # student_blacklist
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
