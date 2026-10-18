
from alembic import op
import sqlalchemy as sa


revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "modules",
        sa.Column(
            "id",
            sa.BigInteger(),
            sa.Identity(always=True),
            primary_key=True,
        ),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column(
            "description",
            sa.Text(),
            nullable=False,
            server_default=sa.text("''"),
        ),
        sa.Column(
            "environment",
            sa.String(length=30),
            nullable=False,
            server_default=sa.text("'development'"),
        ),
        sa.Column(
            "status",
            sa.String(length=30),
            nullable=False,
            server_default=sa.text("'registered'"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_table(
        "module_events",
        sa.Column(
            "id",
            sa.BigInteger(),
            sa.Identity(always=True),
            primary_key=True,
        ),
        sa.Column("module_id", sa.BigInteger(), nullable=False),
        sa.Column("action", sa.String(length=30), nullable=False),
        sa.Column("previous_status", sa.String(length=30), nullable=False),
        sa.Column("new_status", sa.String(length=30), nullable=False),
        sa.Column(
            "result",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'success'"),
        ),
        sa.Column(
            "details",
            sa.Text(),
            nullable=False,
            server_default=sa.text("''"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["module_id"],
            ["modules.id"],
            ondelete="RESTRICT",
        ),
    )

    op.create_index(
        "idx_module_events_module_created",
        "module_events",
        ["module_id", "created_at"],
        unique=False,
        postgresql_ops={"created_at": "DESC"},
    )


def downgrade():
    op.drop_index(
        "idx_module_events_module_created",
        table_name="module_events",
    )
    op.drop_table("module_events")
    op.drop_table("modules")
