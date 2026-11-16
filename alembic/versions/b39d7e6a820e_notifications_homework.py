"""Add personal notifications and assigned homework."""
from alembic import op
import sqlalchemy as sa

revision = "b39d7e6a820e"
down_revision = "a28c6e5f719d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "homework",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("assigned_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("comment", sa.Text()),
        sa.Column("url", sa.String(2048), nullable=False),
        sa.Column("due_date", sa.Date()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_homework_user_created", "homework", ["user_id", "created_at", "id"])
    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("homework_id", sa.Integer(), sa.ForeignKey("homework.id", ondelete="CASCADE"), unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_notifications_user_created", "notifications", ["user_id", "created_at", "id"])
    op.create_index("ix_notifications_user_read", "notifications", ["user_id", "read_at"])


def downgrade() -> None:
    op.drop_table("notifications")
    op.drop_table("homework")
