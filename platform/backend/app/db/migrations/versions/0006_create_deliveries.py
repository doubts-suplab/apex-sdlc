"""create deliveries

Revision ID: 8d4e2f9c7b31
Revises: 7c3d1e8b6a20
Create Date: 2026-08-15 00:00:00.000000+00:00

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8d4e2f9c7b31'
down_revision: Union[str, None] = '7c3d1e8b6a20'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'deliveries',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('project_id', sa.Uuid(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='proposed'),
        sa.Column('priority', sa.String(length=20), nullable=False, server_default='medium'),
        sa.Column('estimate_points', sa.Integer(), nullable=True),
        sa.Column('target_ref', sa.String(length=255), nullable=True),
        sa.Column('source', sa.String(length=20), nullable=False, server_default='human'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_deliveries_project_id', 'deliveries', ['project_id'])


def downgrade() -> None:
    op.drop_index('ix_deliveries_project_id', table_name='deliveries')
    op.drop_table('deliveries')
