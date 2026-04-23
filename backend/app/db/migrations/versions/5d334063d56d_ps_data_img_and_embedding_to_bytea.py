"""student_ps_data ps_img/embedding ni BYTEA ga o'tkazish

Revision ID: 5d334063d56d
Revises: 82af7de48bff
Create Date: 2026-04-13 12:00:00.000000
"""

import base64
import json
from typing import Sequence, Union

import numpy as np
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5d334063d56d"
down_revision: Union[str, None] = "82af7de48bff"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Yangi binary ustunlarni qo'shish
    op.add_column(
        "student_ps_data",
        sa.Column("ps_img_bin", sa.LargeBinary(), nullable=True),
    )
    op.add_column(
        "student_ps_data",
        sa.Column("embedding_bin", sa.LargeBinary(), nullable=True),
    )

    # 2. Mavjud ma'lumotlarni ko'chirish (base64 → bytes, JSON list → float32 bytes)
    conn = op.get_bind()
    rows = conn.execute(
        sa.text("SELECT id, ps_img, embedding FROM student_ps_data")
    ).fetchall()

    for row in rows:
        ps_img_bin = None
        embedding_bin = None

        ps_img_str = row.ps_img
        if ps_img_str:
            try:
                # "data:image/...;base64,xxx" prefiksni olib tashlash
                if "," in ps_img_str and ps_img_str.index(",") < 80:
                    ps_img_str = ps_img_str.split(",", 1)[1]
                ps_img_bin = base64.b64decode(ps_img_str)
            except Exception:
                ps_img_bin = None

        emb_str = row.embedding
        if emb_str:
            try:
                arr = np.array(json.loads(emb_str), dtype=np.float32)
                embedding_bin = arr.tobytes()
            except Exception:
                embedding_bin = None

        conn.execute(
            sa.text(
                "UPDATE student_ps_data SET ps_img_bin=:img, embedding_bin=:emb WHERE id=:id"
            ),
            {"img": ps_img_bin, "emb": embedding_bin, "id": row.id},
        )

    # 3. Eski ustunlarni o'chirish
    op.drop_column("student_ps_data", "ps_img")
    op.drop_column("student_ps_data", "embedding")

    # 4. Yangi ustunlarni to'g'ri nomga o'zgartirish
    op.alter_column("student_ps_data", "ps_img_bin", new_column_name="ps_img")
    op.alter_column("student_ps_data", "embedding_bin", new_column_name="embedding")


def downgrade() -> None:
    # BYTEA → TEXT ga qaytarish (base64 va JSON)
    op.add_column(
        "student_ps_data",
        sa.Column("ps_img_txt", sa.Text(), nullable=True),
    )
    op.add_column(
        "student_ps_data",
        sa.Column("embedding_txt", sa.Text(), nullable=True),
    )

    conn = op.get_bind()
    rows = conn.execute(
        sa.text("SELECT id, ps_img, embedding FROM student_ps_data")
    ).fetchall()

    for row in rows:
        ps_img_txt = None
        emb_txt = None

        if row.ps_img:
            ps_img_txt = base64.b64encode(row.ps_img).decode("ascii")
        if row.embedding:
            try:
                arr = np.frombuffer(row.embedding, dtype=np.float32)
                emb_txt = json.dumps(arr.tolist())
            except Exception:
                emb_txt = None

        conn.execute(
            sa.text(
                "UPDATE student_ps_data SET ps_img_txt=:img, embedding_txt=:emb WHERE id=:id"
            ),
            {"img": ps_img_txt, "emb": emb_txt, "id": row.id},
        )

    op.drop_column("student_ps_data", "ps_img")
    op.drop_column("student_ps_data", "embedding")
    op.alter_column("student_ps_data", "ps_img_txt", new_column_name="ps_img")
    op.alter_column("student_ps_data", "embedding_txt", new_column_name="embedding")
