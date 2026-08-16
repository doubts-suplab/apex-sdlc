"""create project_manifests

Revision ID: 9e5f3a2b1c40
Revises: 8d4e2f9c7b31
Create Date: 2026-08-16 00:00:00.000000+00:00

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '9e5f3a2b1c40'
down_revision: Union[str, None] = '8d4e2f9c7b31'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# JSONB on PostgreSQL (production); generic JSON elsewhere (SQLite in tests) so the schema compiles.
_JSON = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql')


def upgrade() -> None:
    op.create_table(
        'project_manifests',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('project_id', sa.Uuid(), nullable=False),
        sa.Column('domain', sa.String(length=50), nullable=True),
        sa.Column('governance_profile', sa.String(length=50), nullable=True),
        sa.Column('coverage_threshold', sa.Integer(), nullable=True),
        sa.Column('compliance_frameworks', _JSON, nullable=False),
        sa.Column('resolved_packs', _JSON, nullable=False),
        sa.Column('engine', sa.String(length=20), nullable=True),
        sa.Column('source_ref', sa.String(length=500), nullable=True),
        sa.Column('raw', _JSON, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('project_id', name='uq_project_manifests_project_id'),
    )
    op.create_index('ix_project_manifests_project_id', 'project_manifests', ['project_id'])


def downgrade() -> None:
    op.drop_index('ix_project_manifests_project_id', table_name='project_manifests')
    op.drop_table('project_manifests')
