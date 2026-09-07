"""add notification content and event deduplication"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0004_notifications"
down_revision = "0003_outbox"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("notifications", sa.Column("event_id", UUID(as_uuid=True), nullable=True))
    op.add_column("notifications", sa.Column("title", sa.String(255), nullable=True))
    op.add_column("notifications", sa.Column("message", sa.Text(), nullable=True))
    op.add_column("notifications", sa.Column("read_at", sa.DateTime(timezone=True), nullable=True))
    op.create_unique_constraint("uq_notifications_event_id", "notifications", ["event_id"])
    op.create_index("ix_notifications_event_id", "notifications", ["event_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_notifications_event_id", table_name="notifications")
    op.drop_constraint("uq_notifications_event_id", "notifications", type_="unique")
    op.drop_column("notifications", "read_at")
    op.drop_column("notifications", "message")
    op.drop_column("notifications", "title")
    op.drop_column("notifications", "event_id")
