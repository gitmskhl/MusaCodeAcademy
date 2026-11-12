"""Add optional course icon."""
from alembic import op
import sqlalchemy as sa

revision = "e06a4c9d532b"
down_revision = "d95f3b8c421a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("courses", sa.Column("icon_url", sa.String(500), nullable=True))


def downgrade() -> None:
    op.drop_column("courses", "icon_url")
