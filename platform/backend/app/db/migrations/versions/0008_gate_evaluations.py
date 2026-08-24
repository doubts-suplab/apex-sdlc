"""gate evaluations (and merge the two open heads)

Persists phase-gate evaluations (ROADMAP Phase 5) and, in the same step, merges the two migration
heads that had forked off ``0005`` (``9e4f2a7b1c30`` arb_submissions and ``9e5f3a2b1c40``
project_manifests) so ``alembic upgrade head`` is unambiguous again.

Revision ID: a1b2c3d4e5f0
Revises: 9e4f2a7b1c30, 9e5f3a2b1c40
Create Date: 2026-08-24 00:00:00.000000+00:00

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f0'
down_revision: Union[str, Sequence[str], None] = ('9e4f2a7b1c30', '9e5f3a2b1c40')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'gate_evaluations',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('project_id', sa.Uuid(), nullable=False),
        sa.Column('phase', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False, server_default=''),
        sa.Column('bypass_total', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('evaluated_by', sa.String(length=100), nullable=False, server_default=''),
        sa.Column('checks', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_gate_evaluations_project_id', 'gate_evaluations', ['project_id'])
    op.create_index('ix_gate_evaluations_phase', 'gate_evaluations', ['phase'])


def downgrade() -> None:
    op.drop_index('ix_gate_evaluations_phase', table_name='gate_evaluations')
    op.drop_index('ix_gate_evaluations_project_id', table_name='gate_evaluations')
    op.drop_table('gate_evaluations')
