"""enforce ownership, valid states and non-negative values"""

import sqlalchemy as sa
from alembic import op

revision = "0006_persistence_constraints"
down_revision = "0005_auth_sessions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("videos", "user_id", existing_type=sa.UUID(), nullable=False)
    op.create_check_constraint("ck_videos_file_size_nonnegative", "videos", "file_size >= 0")
    op.create_check_constraint(
        "ck_videos_progress_range", "videos", "progress >= 0 AND progress <= 100"
    )
    op.create_check_constraint(
        "ck_videos_status",
        "videos",
        "status IN ('UPLOADING', 'QUEUED', 'PROCESSING', 'COMPLETED', 'FAILED')",
    )
    op.create_check_constraint(
        "ck_processing_jobs_attempt_nonnegative", "processing_jobs", "attempt >= 0"
    )
    op.create_check_constraint(
        "ck_processing_jobs_status",
        "processing_jobs",
        "status IN ('UPLOADING', 'QUEUED', 'PROCESSING', 'COMPLETED', 'FAILED')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_processing_jobs_status", "processing_jobs", type_="check")
    op.drop_constraint("ck_processing_jobs_attempt_nonnegative", "processing_jobs", type_="check")
    op.drop_constraint("ck_videos_status", "videos", type_="check")
    op.drop_constraint("ck_videos_progress_range", "videos", type_="check")
    op.drop_constraint("ck_videos_file_size_nonnegative", "videos", type_="check")
    op.alter_column("videos", "user_id", existing_type=sa.UUID(), nullable=True)
