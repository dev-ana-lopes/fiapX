"""transactional outbox for reliable video publication"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0003_outbox"
down_revision = "0002_video_metadata"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "outbox_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("event_type", sa.String(120), nullable=False),
        sa.Column("aggregate_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.String(500)),
    )


def downgrade() -> None:
    op.drop_table("outbox_events")
