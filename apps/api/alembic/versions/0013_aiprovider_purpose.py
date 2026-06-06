"""Add purpose to ai_providers

Revision ID: 0013
Revises: 0012
"""
from alembic import op
import sqlalchemy as sa

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Adding string column 'purpose' to ai_providers with default 'embedding'
    op.add_column("ai_providers", sa.Column("purpose", sa.String(32), server_default="embedding", nullable=False))

def downgrade() -> None:
    op.drop_column("ai_providers", "purpose")
