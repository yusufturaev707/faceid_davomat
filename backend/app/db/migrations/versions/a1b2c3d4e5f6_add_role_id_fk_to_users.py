"""add role_id fk to users

Revision ID: a1b2c3d4e5f6
Revises: 82af7de48bff
Create Date: 2026-03-16 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '82af7de48bff'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. roles jadvaliga default qiymatlar qo'shish (agar yo'q bo'lsa)
    # key=1: Admin, key=2: Rahbar, key=3: Vakil
    op.execute("""
        INSERT INTO roles (name, key, is_active)
        SELECT 'Admin', 1, true
        WHERE NOT EXISTS (SELECT 1 FROM roles WHERE key = 1);
    """)
    op.execute("""
        INSERT INTO roles (name, key, is_active)
        SELECT 'Rahbar', 2, true
        WHERE NOT EXISTS (SELECT 1 FROM roles WHERE key = 2);
    """)
    op.execute("""
        INSERT INTO roles (name, key, is_active)
        SELECT 'Vakil', 3, true
        WHERE NOT EXISTS (SELECT 1 FROM roles WHERE key = 3);
    """)

    # 2. role_id column qo'shish (nullable)
    op.add_column('users', sa.Column('role_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_users_role_id'), 'users', ['role_id'], unique=False)
    op.create_foreign_key('fk_users_role_id', 'users', 'roles', ['role_id'], ['id'])

    # 3. Mavjud userlarning role string qiymatini role_id ga migrate qilish
    # "admin" -> key=1 (Admin), qolganlar -> key=3 (Vakil)
    op.execute("""
        UPDATE users
        SET role_id = (SELECT id FROM roles WHERE key = 1)
        WHERE role = 'admin';
    """)
    op.execute("""
        UPDATE users
        SET role_id = (SELECT id FROM roles WHERE key = 3)
        WHERE role != 'admin' OR role IS NULL;
    """)

    # 4. Eski role string column o'chirish
    op.drop_column('users', 'role')


def downgrade() -> None:
    # role string column qaytarish
    op.add_column('users', sa.Column('role', sa.String(20), nullable=True))

    # role_id dan role string ga qaytarish
    op.execute("""
        UPDATE users
        SET role = (SELECT name FROM roles WHERE roles.id = users.role_id)
        WHERE role_id IS NOT NULL;
    """)
    op.execute("UPDATE users SET role = 'operator' WHERE role IS NULL;")
    op.execute("ALTER TABLE users ALTER COLUMN role SET NOT NULL;")
    op.execute("ALTER TABLE users ALTER COLUMN role SET DEFAULT 'operator';")

    op.drop_constraint('fk_users_role_id', 'users', type_='foreignkey')
    op.drop_index(op.f('ix_users_role_id'), table_name='users')
    op.drop_column('users', 'role_id')
