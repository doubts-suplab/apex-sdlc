"""tool call audits

Revision ID: 7c3d1e8b6a20
Revises: 5b2e7a4c9f10
Create Date: 2026-08-14 00:00:00.000000+00:00

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7c3d1e8b6a20'
down_revision: Union[str, None] = '5b2e7a4c9f10'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'tool_call_audits',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('actor', sa.String(length=255), nullable=False),
        sa.Column('tool', sa.String(length=100), nullable=False),
        sa.Column('system', sa.String(length=50), nullable=False),
        sa.Column('executed', sa.Boolean(), nullable=False),
        sa.Column('detail', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('tool_call_audits')
