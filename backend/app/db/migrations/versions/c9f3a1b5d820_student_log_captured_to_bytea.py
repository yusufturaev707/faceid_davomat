"""student_logs.first_captured/last_captured TEXT -> BYTEA

Revision ID: c9f3a1b5d820
Revises: b8e4f2a91c37
Create Date: 2026-04-13 15:30:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c9f3a1b5d820"
down_revision: Union[str, None] = "b8e4f2a91c37"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Mavjud qiymatlar base64-string shaklida saqlangan bo'lishi mumkin.
    # Data URL prefiksini olib tashlab, base64 decode qilamiz.
    # Base64 bo'lmagan / buzuq qiymatlar NULL ga o'tkaziladi.
    op.execute(
        """
        UPDATE student_logs
        SET first_captured = regexp_replace(first_captured, '^data:[^,]*,', '')
        WHERE first_captured LIKE 'data:%';
        """
    )
    op.execute(
        """
        UPDATE student_logs
        SET last_captured = regexp_replace(last_captured, '^data:[^,]*,', '')
        WHERE last_captured LIKE 'data:%';
        """
    )
    # Base64 bo'lmagan qiymatlarni NULL qilamiz (decode xato bermasin)
    op.execute(
        """
        UPDATE student_logs
        SET first_captured = NULL
        WHERE first_captured IS NOT NULL
          AND first_captured !~ '^[A-Za-z0-9+/=\\s]+$';
        """
    )
    op.execute(
        """
        UPDATE student_logs
        SET last_captured = NULL
        WHERE last_captured IS NOT NULL
          AND last_captured !~ '^[A-Za-z0-9+/=\\s]+$';
        """
    )

    op.execute(
        """
        ALTER TABLE student_logs
        ALTER COLUMN first_captured TYPE BYTEA
        USING CASE WHEN first_captured IS NULL THEN NULL
                   ELSE decode(replace(replace(first_captured, E'\\n', ''), E'\\r', ''), 'base64')
              END
        """
    )
    op.execute(
        """
        ALTER TABLE student_logs
        ALTER COLUMN last_captured TYPE BYTEA
        USING CASE WHEN last_captured IS NULL THEN NULL
                   ELSE decode(replace(replace(last_captured, E'\\n', ''), E'\\r', ''), 'base64')
              END
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE student_logs
        ALTER COLUMN first_captured TYPE TEXT
        USING CASE WHEN first_captured IS NULL THEN NULL
                   ELSE encode(first_captured, 'base64')
              END
        """
    )
    op.execute(
        """
        ALTER TABLE student_logs
        ALTER COLUMN last_captured TYPE TEXT
        USING CASE WHEN last_captured IS NULL THEN NULL
                   ELSE encode(last_captured, 'base64')
              END
        """
    )
