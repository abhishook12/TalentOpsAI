"""add canonical company fields

Revision ID: 44f8fdce07d3
Revises: bc965ada9967
Create Date: 2026-08-12 21:29:11.505837

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '44f8fdce07d3'
down_revision: Union[str, Sequence[str], None] = 'bc965ada9967'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('companies', sa.Column('primary_domain', sa.String(length=255), nullable=True))
    op.add_column('companies', sa.Column('canonical_name', sa.String(length=255), nullable=True))
    op.add_column('companies', sa.Column('logo_url', sa.String(length=500), nullable=True))
    op.add_column('companies', sa.Column('logo_source', sa.String(length=100), nullable=True))
    op.add_column('companies', sa.Column('identity_confidence', sa.Integer(), nullable=True, server_default='0'))
    op.add_column('companies', sa.Column('verification_status', sa.String(length=50), nullable=True, server_default='unverified'))
    op.add_column('companies', sa.Column('last_verified_at', sa.TIMESTAMP(), nullable=True))
    
    op.create_index(op.f('ix_companies_primary_domain'), 'companies', ['primary_domain'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_companies_primary_domain'), table_name='companies')
    op.drop_column('companies', 'last_verified_at')
    op.drop_column('companies', 'verification_status')
    op.drop_column('companies', 'identity_confidence')
    op.drop_column('companies', 'logo_source')
    op.drop_column('companies', 'logo_url')
    op.drop_column('companies', 'canonical_name')
    op.drop_column('companies', 'primary_domain')
