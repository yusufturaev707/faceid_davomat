"""Grant student_log:create to desktop operator roles (Hududiy/Markaziy vakil)

Desktop client `Hududiy vakil` yoki `Markaziy vakil` rolida login qilib,
`/students/logs/bulk` endpointga attendance yozuvlarini yuboradi. Oldingi
seed'da bu rollarga `student_log:create` permission biriktirilmagan edi —
natijada 403 Forbidden. Shu migration idempotent tarzda kerakli permission'larni
biriktiradi.

Revision ID: e5a7c1b93f10
Revises: m1h0234d8e2
Create Date: 2026-04-17 10:00:00.000000
"""
from typing import Sequence, Union

from alembic import op


revision: str = "e5a7c1b93f10"
down_revision: Union[str, None] = "m1h0234d8e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


DESKTOP_ROLE_NAMES = ("Hududiy vakil", "Markaziy vakil")
DESKTOP_PERMS = (
    "student_log:create",
    "student_log:read",
    "cheating_log:create",
    "test_session:read",
    "student:read",
)


def upgrade() -> None:
    conn = op.get_bind()
    for role_name in DESKTOP_ROLE_NAMES:
        for perm_code in DESKTOP_PERMS:
            conn.exec_driver_sql(
                """
                INSERT INTO role_permissions (role_id, permission_id)
                SELECT r.id, p.id
                  FROM roles r
                  JOIN permissions p ON p.codename = %s
                 WHERE r.name = %s
                ON CONFLICT (role_id, permission_id) DO NOTHING
                """,
                (perm_code, role_name),
            )


def downgrade() -> None:
    conn = op.get_bind()
    for role_name in DESKTOP_ROLE_NAMES:
        for perm_code in DESKTOP_PERMS:
            conn.exec_driver_sql(
                """
                DELETE FROM role_permissions
                 WHERE role_id IN (SELECT id FROM roles WHERE name = %s)
                   AND permission_id IN (SELECT id FROM permissions WHERE codename = %s)
                """,
                (role_name, perm_code),
            )
