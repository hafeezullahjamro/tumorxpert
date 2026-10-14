"""Persist measured processing progress for navigation and refresh recovery."""
from alembic import op
import sqlalchemy as sa

revision = "20261014_0002"
down_revision = "20241027_0001"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("studies", sa.Column("progress", sa.JSON(), nullable=True))


def downgrade():
    op.drop_column("studies", "progress")
