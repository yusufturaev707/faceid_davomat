"""Add verify_faces table

Revision ID: c48f2a1e3d5b
Revises: b37c1cf0246b
Create Date: 2026-03-09 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c48f2a1e3d5b'
down_revision: Union[str, None] = 'b37c1cf0246b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('verify_faces',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('timestamp', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('ps_img', sa.String(length=255), nullable=True),
    sa.Column('lv_img', sa.String(length=255), nullable=True),
    sa.Column('ps_file_size', sa.Integer(), nullable=False),
    sa.Column('lv_file_size', sa.Integer(), nullable=False),
    sa.Column('ps_width', sa.Integer(), nullable=False),
    sa.Column('ps_height', sa.Integer(), nullable=False),
    sa.Column('lv_width', sa.Integer(), nullable=False),
    sa.Column('lv_height', sa.Integer(), nullable=False),
    sa.Column('ps_detection', sa.Boolean(), nullable=False),
    sa.Column('lv_detection', sa.Boolean(), nullable=False),
    sa.Column('detection', sa.Boolean(), nullable=False),
    sa.Column('response_time', sa.Float(), nullable=False),
    sa.Column('score', sa.Float(), nullable=False),
    sa.Column('thresh_score', sa.Float(), nullable=False),
    sa.Column('verified', sa.Boolean(), nullable=False),
    sa.Column('error_message', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_verify_faces_id'), 'verify_faces', ['id'], unique=False)
    op.create_index(op.f('ix_verify_faces_timestamp'), 'verify_faces', ['timestamp'], unique=False)
    op.create_index(op.f('ix_verify_faces_user_id'), 'verify_faces', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_verify_faces_user_id'), table_name='verify_faces')
    op.drop_index(op.f('ix_verify_faces_timestamp'), table_name='verify_faces')
    op.drop_index(op.f('ix_verify_faces_id'), table_name='verify_faces')
    op.drop_table('verify_faces')
