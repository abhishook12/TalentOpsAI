"""Add RepairLog and Data Quality flags

Revision ID: bc965ada9967
Revises: f2d95dfa5fd1
Create Date: 2026-08-06 03:21:00.107441

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bc965ada9967'
down_revision: Union[str, Sequence[str], None] = 'f2d95dfa5fd1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('repair_logs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('entity_type', sa.String(length=50), nullable=False),
    sa.Column('entity_id', sa.Integer(), nullable=False),
    sa.Column('field_name', sa.String(length=100), nullable=False),
    sa.Column('old_value', sa.Text(), nullable=True),
    sa.Column('new_value', sa.Text(), nullable=True),
    sa.Column('confidence', sa.Integer(), nullable=True),
    sa.Column('evidence', sa.Text(), nullable=True),
    sa.Column('source', sa.String(length=100), nullable=True),
    sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_repair_logs_created_at'), 'repair_logs', ['created_at'], unique=False)
    op.create_index(op.f('ix_repair_logs_entity_id'), 'repair_logs', ['entity_id'], unique=False)
    op.create_index(op.f('ix_repair_logs_entity_type'), 'repair_logs', ['entity_type'], unique=False)
    op.create_index(op.f('ix_repair_logs_id'), 'repair_logs', ['id'], unique=False)
    
    op.add_column('companies', sa.Column('completeness_score', sa.Integer(), nullable=True))
    op.add_column('companies', sa.Column('quality_flags', sa.Text(), nullable=True))
    op.add_column('companies', sa.Column('merged_into_id', sa.Integer(), nullable=True))
    op.add_column('companies', sa.Column('canonical_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_companies_canonical_id'), 'companies', ['canonical_id'], unique=False)
    op.create_index(op.f('ix_companies_merged_into_id'), 'companies', ['merged_into_id'], unique=False)
    op.create_foreign_key(None, 'companies', 'companies', ['merged_into_id'], ['company_id'], ondelete='SET NULL')
    op.create_foreign_key(None, 'companies', 'companies', ['canonical_id'], ['company_id'], ondelete='SET NULL')
    
    op.add_column('recruiters', sa.Column('quality_flags', sa.Text(), nullable=True))
    op.add_column('recruiters', sa.Column('merged_into_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_recruiters_merged_into_id'), 'recruiters', ['merged_into_id'], unique=False)
    op.create_foreign_key(None, 'recruiters', 'recruiters', ['merged_into_id'], ['recruiter_id'], ondelete='SET NULL')


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(None, 'recruiters', type_='foreignkey')
    op.drop_index(op.f('ix_recruiters_merged_into_id'), table_name='recruiters')
    op.drop_column('recruiters', 'merged_into_id')
    op.drop_column('recruiters', 'quality_flags')
    
    op.drop_constraint(None, 'companies', type_='foreignkey')
    op.drop_constraint(None, 'companies', type_='foreignkey')
    op.drop_index(op.f('ix_companies_merged_into_id'), table_name='companies')
    op.drop_index(op.f('ix_companies_canonical_id'), table_name='companies')
    op.drop_column('companies', 'canonical_id')
    op.drop_column('companies', 'merged_into_id')
    op.drop_column('companies', 'quality_flags')
    op.drop_column('companies', 'completeness_score')
    
    op.drop_index(op.f('ix_repair_logs_id'), table_name='repair_logs')
    op.drop_index(op.f('ix_repair_logs_entity_type'), table_name='repair_logs')
    op.drop_index(op.f('ix_repair_logs_entity_id'), table_name='repair_logs')
    op.drop_index(op.f('ix_repair_logs_created_at'), table_name='repair_logs')
    op.drop_table('repair_logs')
