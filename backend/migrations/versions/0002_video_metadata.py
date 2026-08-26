"""store upload metadata required by the API contract"""

import sqlalchemy as sa
from alembic import op

revision = "0002_video_metadata"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "videos",
        sa.Column(
            "content_type",
            sa.String(120),
            nullable=False,
            server_default="application/octet-stream",
        ),
    )
    op.add_column(
        "videos", sa.Column("file_size", sa.Integer(), nullable=False, server_default="0")
    )


def downgrade() -> None:
    op.drop_column("videos", "file_size")
    op.drop_column("videos", "content_type")
