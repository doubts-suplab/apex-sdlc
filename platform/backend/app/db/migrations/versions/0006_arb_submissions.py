"""arb submissions

Revision ID: 9e4f2a7b1c30
Revises: 7c3d1e8b6a20
Create Date: 2026-08-14 01:00:00.000000+00:00

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9e4f2a7b1c30'
down_revision: Union[str, None] = '7c3d1e8b6a20'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'arb_submissions',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('project_id', sa.Uuid(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('summary', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False),
        sa.Column('submitted_by', sa.String(length=255), nullable=False),
        sa.Column('submitter_persona', sa.String(length=20), nullable=False),
        sa.Column('reviewed_by', sa.String(length=255), nullable=True),
        sa.Column('reviewer_persona', sa.String(length=20), nullable=True),
        sa.Column('decision_rationale', sa.Text(), nullable=True),
        sa.Column('decided_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_arb_submissions_project_id'), 'arb_submissions', ['project_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_arb_submissions_project_id'), table_name='arb_submissions')
    op.drop_table('arb_submissions')
