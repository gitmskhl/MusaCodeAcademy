"""Add per-user AI assistance, saved hints and persistent daily quota."""
from alembic import op
import sqlalchemy as sa

revision = "f17b5da6420c"
down_revision = "e06a4c9d532b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("ai_assistance_enabled", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("submissions", sa.Column("ai_hint", sa.Text(), nullable=True))
    op.create_table(
        "ai_hint_usage",
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("day", sa.Date(), primary_key=True),
        sa.Column("requests_count", sa.Integer(), nullable=False),
        sa.CheckConstraint("requests_count BETWEEN 0 AND 10", name="ck_ai_hint_usage_count"),
    )


def downgrade() -> None:
    op.drop_table("ai_hint_usage")
    op.drop_column("submissions", "ai_hint")
    op.drop_column("users", "ai_assistance_enabled")
