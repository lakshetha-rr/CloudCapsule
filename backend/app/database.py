
import os
from urllib.parse import urlsplit

import psycopg
from psycopg.rows import dict_row


def get_database_url() -> str:
    database_url = os.getenv("DATABASE_URL", "").strip()

    if not database_url:
        raise RuntimeError(
            "DATABASE_URL environment variable is not set"
        )

    try:
        parsed_url = urlsplit(database_url)
        hostname = parsed_url.hostname
        database_name = parsed_url.path.strip("/")
        port = parsed_url.port
    except ValueError:
        raise RuntimeError(
            "DATABASE_URL is not a valid PostgreSQL URL"
        ) from None

    if (
        parsed_url.scheme not in {"postgresql", "postgres"}
        or not hostname
        or not database_name
        or parsed_url.query
        or parsed_url.fragment
        or (port is not None and not 1 <= port <= 65535)
    ):
        raise RuntimeError(
            "DATABASE_URL must be a valid PostgreSQL URL "
            "with a hostname and database name"
        )

    return database_url


def get_connection():
    return psycopg.connect(
        get_database_url(),
        row_factory=dict_row,
        connect_timeout=5,
    )