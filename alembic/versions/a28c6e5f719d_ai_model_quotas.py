"""Add per-user AI model allocations and per-model daily usage."""
from alembic import op
import sqlalchemy as sa

revision = "a28c6e5f719d"
down_revision = "f17b5da6420c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("ai_daily_limit", sa.Integer(), nullable=False, server_default="10"))
    op.add_column("users", sa.Column("ai_model_limits", sa.JSON(), nullable=True))
    op.create_check_constraint("ck_users_ai_daily_limit", "users", "ai_daily_limit BETWEEN 1 AND 1000")
    op.add_column("submissions", sa.Column("ai_hint_model", sa.String(255), nullable=True))
    op.drop_constraint("ck_ai_hint_usage_count", "ai_hint_usage", type_="check")
    op.create_check_constraint("ck_ai_hint_usage_count", "ai_hint_usage", "requests_count >= 0")
    op.create_table(
        "ai_model_hint_usage",
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("day", sa.Date(), primary_key=True),
        sa.Column("model", sa.String(255), primary_key=True),
        sa.Column("requests_count", sa.Integer(), nullable=False),
        sa.CheckConstraint("requests_count >= 0", name="ck_ai_model_hint_usage_count"),
    )


def downgrade() -> None:
    op.drop_table("ai_model_hint_usage")
    op.drop_constraint("ck_ai_hint_usage_count", "ai_hint_usage", type_="check")
    # Preserve historical counters above 10; the previous application already
    # refuses requests when the count reaches its fixed daily limit.
    op.execute("ALTER TABLE ai_hint_usage ADD CONSTRAINT ck_ai_hint_usage_count "
               "CHECK (requests_count BETWEEN 0 AND 10) NOT VALID")
    op.drop_column("submissions", "ai_hint_model")
    op.drop_constraint("ck_users_ai_daily_limit", "users", type_="check")
    op.drop_column("users", "ai_model_limits")
    op.drop_column("users", "ai_daily_limit")
