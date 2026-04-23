"""Deduplicate and enforce uniqueness on cheating_logs and student_blacklist.

Desktop clientdan keladigan bulk-sync endi CheatingLog ni student_id bo'yicha
upsert qiladi (bitta student uchun bitta yozuv) va StudentBlacklist ga aynan
bir imei ni faqat bir marta yozadi. Shu sababli ikkala jadvalga ham tegishli
UNIQUE cheklovlar qo'shiladi; avval mavjud dublikatlar tozalanadi.

- cheating_logs: (mavjud bo'lsa) created_at/updated_at tegilmaydi,
  unique(student_id) qo'shiladi. Dedupe: har bir student_id bo'yicha eng
  yangi (max id) qator qoldiriladi.
- student_blacklist: (mavjud bo'lsa) created_at tegilmaydi,
  unique(imei) qo'shiladi. Dedupe: har bir imei bo'yicha eng eski (min id)
  qator qoldiriladi; NULL imei qatorlari tegilmaydi.

Migration idempotent — ustunlar/cheklovlar allaqachon mavjud bo'lsa o'tkazib
yuboriladi (drift bo'lgan DB'larda ham xavfsiz).

Revision ID: f6b2d91a5c40
Revises: e5a7c1b93f10
Create Date: 2026-04-17 14:30:00.000000
"""
from typing import Sequence, Union

from alembic import op


revision: str = "f6b2d91a5c40"
down_revision: Union[str, None] = "e5a7c1b93f10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── cheating_logs ──
    op.execute(
        """
        DELETE FROM cheating_logs a
        USING cheating_logs b
        WHERE a.student_id = b.student_id AND a.id < b.id
        """
    )
    op.execute(
        """
        ALTER TABLE cheating_logs
        ADD COLUMN IF NOT EXISTS created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        """
    )
    op.execute(
        """
        ALTER TABLE cheating_logs
        ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'uq_cheating_logs_student_id'
            ) THEN
                ALTER TABLE cheating_logs
                ADD CONSTRAINT uq_cheating_logs_student_id UNIQUE (student_id);
            END IF;
        END $$;
        """
    )

    # ── student_blacklist ──
    op.execute(
        """
        DELETE FROM student_blacklist a
        USING student_blacklist b
        WHERE a.imei IS NOT NULL
          AND a.imei = b.imei
          AND a.id > b.id
        """
    )
    op.execute(
        """
        ALTER TABLE student_blacklist
        ADD COLUMN IF NOT EXISTS created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'uq_student_blacklist_imei'
            ) THEN
                ALTER TABLE student_blacklist
                ADD CONSTRAINT uq_student_blacklist_imei UNIQUE (imei);
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE student_blacklist DROP CONSTRAINT IF EXISTS uq_student_blacklist_imei"
    )
    op.execute(
        "ALTER TABLE cheating_logs DROP CONSTRAINT IF EXISTS uq_cheating_logs_student_id"
    )
