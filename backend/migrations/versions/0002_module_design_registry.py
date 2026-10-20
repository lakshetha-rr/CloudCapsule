from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0002_module_design_registry"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "modules",
        sa.Column(
            "design_version",
            sa.String(length=30),
            nullable=False,
            server_default=sa.text("'1.0.0'"),
        ),
    )
    op.add_column(
        "modules",
        sa.Column(
            "deployment_model",
            sa.String(length=30),
            nullable=False,
            server_default=sa.text("'container'"),
        ),
    )
    op.add_column(
        "modules",
        sa.Column(
            "cpu_units",
            sa.BigInteger(),
            nullable=False,
            server_default=sa.text("256"),
        ),
    )
    op.add_column(
        "modules",
        sa.Column(
            "memory_mb",
            sa.BigInteger(),
            nullable=False,
            server_default=sa.text("512"),
        ),
    )
    op.add_column(
        "modules",
        sa.Column(
            "min_replicas",
            sa.BigInteger(),
            nullable=False,
            server_default=sa.text("1"),
        ),
    )
    op.add_column(
        "modules",
        sa.Column(
            "max_replicas",
            sa.BigInteger(),
            nullable=False,
            server_default=sa.text("2"),
        ),
    )
    op.add_column(
        "modules",
        sa.Column(
            "health_check_path",
            sa.String(length=200),
            nullable=False,
            server_default=sa.text("'/health'"),
        ),
    )
    op.add_column(
        "modules",
        sa.Column(
            "network_access",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'internal'"),
        ),
    )
    op.add_column(
        "modules",
        sa.Column(
            "backup_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "modules",
        sa.Column(
            "design_spec",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )


def downgrade():
    for column in (
        "design_spec",
        "backup_enabled",
        "network_access",
        "health_check_path",
        "max_replicas",
        "min_replicas",
        "memory_mb",
        "cpu_units",
        "deployment_model",
        "design_version",
    ):
        op.drop_column("modules", column)