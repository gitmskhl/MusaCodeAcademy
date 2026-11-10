"""Add optional Kinescope promo video to courses."""
from alembic import op
import sqlalchemy as sa

revision = "c84e2a9f713b"
down_revision = "b71d9e4a620f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("courses", sa.Column("promo_video_url", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("courses", "promo_video_url")
