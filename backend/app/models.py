from sqlalchemy import (
    BigInteger,
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

metadata = MetaData()

modules = Table(
    "modules",
    metadata,
    Column("id", BigInteger, Identity(always=True), primary_key=True),
    Column("name", String(100), nullable=False),
    Column("description", Text, nullable=False, server_default=text("''")),
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
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)

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
    Column("result", String(20), nullable=False, server_default=text("'success'")),
    Column("details", Text, nullable=False, server_default=text("''")),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)

Index(
    "idx_module_events_module_created",
    module_events.c.module_id,
    module_events.c.created_at.desc(),
)