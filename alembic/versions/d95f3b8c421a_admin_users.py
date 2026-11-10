"""Account blocking and administrative submission indexes."""
from alembic import op
import sqlalchemy as sa

revision = "d95f3b8c421a"
down_revision = "c84e2a9f713b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("blocked_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("block_reason", sa.String(500), nullable=True))
    op.create_index("ix_submissions_submitted_at_id", "submissions", ["submitted_at", "id"])
    op.create_index("ix_submissions_user_submitted_at", "submissions", ["user_id", "submitted_at"])


def downgrade() -> None:
    op.drop_index("ix_submissions_user_submitted_at", table_name="submissions")
    op.drop_index("ix_submissions_submitted_at_id", table_name="submissions")
    op.drop_column("users", "block_reason")
    op.drop_column("users", "blocked_at")
