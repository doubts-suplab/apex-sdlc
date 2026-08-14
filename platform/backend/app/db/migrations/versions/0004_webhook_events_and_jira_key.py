"""webhook events dedup + jira project key

Revision ID: 5b2e7a4c9f10
Revises: 3a1f2c9d4e70
Create Date: 2026-08-12 00:00:00.000000+00:00

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5b2e7a4c9f10'
down_revision: Union[str, None] = '3a1f2c9d4e70'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('projects', sa.Column('jira_project_key', sa.String(length=50), nullable=True))
    op.create_table(
        'webhook_events',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('source', sa.String(length=20), nullable=False),
        sa.Column('delivery_id', sa.String(length=255), nullable=False),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('source', 'delivery_id', name='uq_webhook_source_delivery'),
    )


def downgrade() -> None:
    op.drop_table('webhook_events')
    op.drop_column('projects', 'jira_project_key')
