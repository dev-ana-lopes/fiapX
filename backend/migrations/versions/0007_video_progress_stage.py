"""store the human-readable processing stage"""

import sqlalchemy as sa
from alembic import op

revision = "0007_video_progress_stage"
down_revision = "0006_persistence_constraints"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "videos",
        sa.Column(
            "progress_stage",
            sa.String(80),
            nullable=False,
            server_default="Aguardando processamento",
        ),
    )
    op.execute(
        "UPDATE videos SET progress_stage = CASE "
        "WHEN status = 'COMPLETED' THEN 'Concluído' "
        "WHEN status = 'FAILED' THEN 'Falha no processamento' "
        "ELSE 'Aguardando processamento' END"
    )


def downgrade() -> None:
    op.drop_column("videos", "progress_stage")
