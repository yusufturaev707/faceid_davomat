"""refresh_tokens: datetime ustunlarini timezone-aware qilish

expires_at / created_at / reuse_detected_at / updated_at avval
TIMESTAMP WITHOUT TIME ZONE edi — psycopg2 ularni naive datetime qilib
qaytarardi va rotate_refresh_token'dagi UTC-aware `now` bilan
solishtirishda "can't compare offset-naive and offset-aware datetimes"
TypeError chiqarardi.

Mavjud qiymatlar UTC deb interpretatsiya qilinadi: create_refresh_token /
revoke_token_family ular doim datetime.now(timezone.utc) bilan yozilgan.

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-05-14 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_COLUMNS = ("expires_at", "created_at", "reuse_detected_at", "updated_at")


def upgrade() -> None:
    # Raw ALTER COLUMN TYPE — Postgres NOT NULL va DEFAULT'larni saqlaydi.
    # USING ... AT TIME ZONE 'UTC': naive qiymat UTC deb o'qiladi.
    for col in _COLUMNS:
        op.execute(
            f"ALTER TABLE refresh_tokens "
            f"ALTER COLUMN {col} TYPE TIMESTAMP WITH TIME ZONE "
            f"USING {col} AT TIME ZONE 'UTC'"
        )


def downgrade() -> None:
    for col in _COLUMNS:
        op.execute(
            f"ALTER TABLE refresh_tokens "
            f"ALTER COLUMN {col} TYPE TIMESTAMP WITHOUT TIME ZONE "
            f"USING {col} AT TIME ZONE 'UTC'"
        )
