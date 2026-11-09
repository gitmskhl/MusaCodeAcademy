"""Add local/server task checking; default existing and new tasks to local."""
from alembic import op
import sqlalchemy as sa


revision = "b71d9e4a620f"
down_revision = "a222acdf1e43"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tasks", sa.Column(
        "checking_mode", sa.String(6), server_default="local", nullable=False,
    ))
    op.create_check_constraint(
        "task_checking_mode", "tasks", "checking_mode IN ('local', 'server')"
    )


def downgrade() -> None:
    op.drop_constraint("task_checking_mode", "tasks", type_="check")
    op.drop_column("tasks", "checking_mode")
