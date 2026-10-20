
from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    MetaData,
    String,
    Table,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB


metadata = MetaData()


# Main module registry.
# Existing modules receive defaults for the new design fields.
modules = Table(
    "modules",
    metadata,
    Column("id", BigInteger, Identity(always=True), primary_key=True),
    Column("name", String(100), nullable=False),
    Column(
        "description",
        Text,
        nullable=False,
        server_default=text("''"),
    ),
    Column(
        "environment",
        String(30),
        nullable=False,
        server_default=text("'development'"),
    ),
    Column(
        "status",
        String(30),
        nullable=False,
        server_default=text("'registered'"),
    ),

    # Module design and versioning
    Column(
        "design_version",
        String(30),
        nullable=False,
        server_default=text("'1.0.0'"),
    ),
    Column(
        "deployment_model",
        String(30),
        nullable=False,
        server_default=text("'container'"),
    ),

    # Compute resources
    Column(
        "cpu_units",
        BigInteger,
        nullable=False,
        server_default=text("256"),
    ),
    Column(
        "memory_mb",
        BigInteger,
        nullable=False,
        server_default=text("512"),
    ),

    # Scaling configuration
    Column(
        "min_replicas",
        BigInteger,
        nullable=False,
        server_default=text("1"),
    ),
    Column(
        "max_replicas",
        BigInteger,
        nullable=False,
        server_default=text("2"),
    ),

    # Health and network configuration
    Column(
        "health_check_path",
        String(200),
        nullable=False,
        server_default=text("'/health'"),
    ),
    Column(
        "network_access",
        String(20),
        nullable=False,
        server_default=text("'internal'"),
    ),

    # Backup and extensible infrastructure design
    Column(
        "backup_enabled",
        Boolean,
        nullable=False,
        server_default=text("false"),
    ),
    Column(
        "design_spec",
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    ),

    Column(
        "created_at",
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    ),
)


# Lifecycle audit history.
# Keep the existing table and index definitions unchanged.
module_events = Table(
    "module_events",
    metadata,
    Column("id", BigInteger, Identity(always=True), primary_key=True),
    Column(
        "module_id",
        BigInteger,
        ForeignKey("modules.id", ondelete="RESTRICT"),
        nullable=False,
    ),
    Column("action", String(30), nullable=False),
    Column("previous_status", String(30), nullable=False),
    Column("new_status", String(30), nullable=False),
    Column(
        "result",
        String(20),
        nullable=False,
        server_default=text("'success'"),
    ),
    Column(
        "details",
        Text,
        nullable=False,
        server_default=text("''"),
    ),
    Column(
        "created_at",
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    ),
)


Index(
    "idx_module_events_module_created",
    module_events.c.module_id,
    module_events.c.created_at.desc(),
)
