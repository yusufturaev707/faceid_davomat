"""add permissions and role_permissions tables with seed data

Revision ID: d2f3a4b5c6e7
Revises: cb805fd06fbd
Create Date: 2026-03-16 14:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd2f3a4b5c6e7'
down_revision: Union[str, None] = 'cb805fd06fbd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. permissions jadvali
    op.create_table(
        'permissions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('codename', sa.String(length=100), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('group', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_permissions_id'), 'permissions', ['id'])
    op.create_index(op.f('ix_permissions_codename'), 'permissions', ['codename'], unique=True)
    op.create_index(op.f('ix_permissions_group'), 'permissions', ['group'])

    # 2. role_permissions M2M jadvali
    op.create_table(
        'role_permissions',
        sa.Column('role_id', sa.Integer(), nullable=False),
        sa.Column('permission_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['permission_id'], ['permissions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('role_id', 'permission_id'),
    )

    # 3. Default permissionlarni seed qilish
    permissions_table = sa.table(
        'permissions',
        sa.column('codename', sa.String),
        sa.column('name', sa.String),
        sa.column('group', sa.String),
    )

    default_permissions = [
        # Foydalanuvchilar
        {'codename': 'user:read', 'name': "Foydalanuvchilarni ko'rish", 'group': 'Foydalanuvchilar'},
        {'codename': 'user:create', 'name': "Foydalanuvchi yaratish", 'group': 'Foydalanuvchilar'},
        {'codename': 'user:update', 'name': "Foydalanuvchini tahrirlash", 'group': 'Foydalanuvchilar'},
        {'codename': 'user:delete', 'name': "Foydalanuvchini o'chirish", 'group': 'Foydalanuvchilar'},
        # Tekshirish
        {'codename': 'verify:photo', 'name': "Foto tekshirish", 'group': 'Tekshirish'},
        {'codename': 'verify:face', 'name': "Yuz solishtirish", 'group': 'Tekshirish'},
        {'codename': 'verify:embedding', 'name': "Embedding olish", 'group': 'Tekshirish'},
        # Loglar
        {'codename': 'log:read', 'name': "Tekshiruv loglarini ko'rish", 'group': 'Loglar'},
        {'codename': 'face_log:read', 'name': "Yuz solishtirish loglarini ko'rish", 'group': 'Loglar'},
        # Dashboard
        {'codename': 'dashboard:read', 'name': "Dashboardni ko'rish", 'group': 'Dashboard'},
        {'codename': 'dashboard:stats', 'name': "Statistikani ko'rish", 'group': 'Dashboard'},
        # API kalitlar
        {'codename': 'api_key:read', 'name': "API kalitlarni ko'rish", 'group': 'API kalitlar'},
        {'codename': 'api_key:create', 'name': "API kalit yaratish", 'group': 'API kalitlar'},
        {'codename': 'api_key:delete', 'name': "API kalitni o'chirish", 'group': 'API kalitlar'},
        # Test sessiyalar
        {'codename': 'test_session:read', 'name': "Test sessiyalarni ko'rish", 'group': 'Test sessiyalar'},
        {'codename': 'test_session:create', 'name': "Test sessiya yaratish", 'group': 'Test sessiyalar'},
        {'codename': 'test_session:update', 'name': "Test sessiyani tahrirlash", 'group': 'Test sessiyalar'},
        {'codename': 'test_session:delete', 'name': "Test sessiyani o'chirish", 'group': 'Test sessiyalar'},
        # Studentlar
        {'codename': 'student:read', 'name': "Studentlarni ko'rish", 'group': 'Studentlar'},
        {'codename': 'student:create', 'name': "Student yaratish", 'group': 'Studentlar'},
        {'codename': 'student:update', 'name': "Studentni tahrirlash", 'group': 'Studentlar'},
        {'codename': 'student:delete', 'name': "Studentni o'chirish", 'group': 'Studentlar'},
        # Student loglar
        {'codename': 'student_log:read', 'name': "Student loglarni ko'rish", 'group': 'Student loglar'},
        {'codename': 'student_log:create', 'name': "Student log yaratish", 'group': 'Student loglar'},
        {'codename': 'student_log:update', 'name': "Student logni tahrirlash", 'group': 'Student loglar'},
        {'codename': 'student_log:delete', 'name': "Student logni o'chirish", 'group': 'Student loglar'},
        # Qoidabuzarliklar
        {'codename': 'cheating_log:read', 'name': "Qoidabuzarliklarni ko'rish", 'group': 'Qoidabuzarliklar'},
        {'codename': 'cheating_log:create', 'name': "Qoidabuzarlik yaratish", 'group': 'Qoidabuzarliklar'},
        {'codename': 'cheating_log:update', 'name': "Qoidabuzarlikni tahrirlash", 'group': 'Qoidabuzarliklar'},
        {'codename': 'cheating_log:delete', 'name': "Qoidabuzarlikni o'chirish", 'group': 'Qoidabuzarliklar'},
        # Sozlamalar (lookup)
        {'codename': 'lookup:read', 'name': "Sozlamalarni ko'rish", 'group': 'Sozlamalar'},
        {'codename': 'lookup:create', 'name': "Sozlama yaratish", 'group': 'Sozlamalar'},
        {'codename': 'lookup:update', 'name': "Sozlamani tahrirlash", 'group': 'Sozlamalar'},
        {'codename': 'lookup:delete', 'name': "Sozlamani o'chirish", 'group': 'Sozlamalar'},
        # Rollar va huquqlar
        {'codename': 'role:read', 'name': "Rollarni ko'rish", 'group': 'Rollar'},
        {'codename': 'role:update', 'name': "Rol permissionlarini tahrirlash", 'group': 'Rollar'},
    ]

    op.bulk_insert(permissions_table, default_permissions)


def downgrade() -> None:
    op.drop_table('role_permissions')
    op.drop_index(op.f('ix_permissions_group'), table_name='permissions')
    op.drop_index(op.f('ix_permissions_codename'), table_name='permissions')
    op.drop_index(op.f('ix_permissions_id'), table_name='permissions')
    op.drop_table('permissions')
