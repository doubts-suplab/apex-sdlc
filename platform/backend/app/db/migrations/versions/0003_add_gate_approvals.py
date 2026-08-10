"""add gate approvals

Revision ID: 3a1f2c9d4e70
Revises: 16897fdb1ce5
Create Date: 2026-08-10 00:00:00.000000+00:00

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3a1f2c9d4e70'
down_revision: Union[str, None] = '16897fdb1ce5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'gate_approvals',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('project_id', sa.Uuid(), nullable=False),
        sa.Column('phase', sa.String(length=50), nullable=False),
        sa.Column('approver_subject', sa.String(length=255), nullable=False),
        sa.Column('approver_persona', sa.String(length=20), nullable=False),
        sa.Column('member_id', sa.Uuid(), nullable=True),
        sa.Column('decision', sa.String(length=20), nullable=False),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['member_id'], ['members.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_gate_approvals_project_id'), 'gate_approvals', ['project_id'], unique=False)
    op.create_index(op.f('ix_gate_approvals_member_id'), 'gate_approvals', ['member_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_gate_approvals_member_id'), table_name='gate_approvals')
    op.drop_index(op.f('ix_gate_approvals_project_id'), table_name='gate_approvals')
    op.drop_table('gate_approvals')
