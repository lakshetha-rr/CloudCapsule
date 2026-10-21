
import os
from urllib.parse import quote, urlsplit

import psycopg
from psycopg.rows import dict_row


def get_database_url() -> str:
    database_url = os.getenv("DATABASE_URL", "").strip()

    if not database_url:
        host = os.getenv("DB_HOST", "").strip()
        name = os.getenv("DB_NAME", "").strip()
        username = os.getenv("DB_USER", "").strip()
        password = os.getenv("DB_PASSWORD", "")
        port = os.getenv("DB_PORT", "5432").strip()

        if not all([host, name, username, password]):
            raise RuntimeError(
                "DATABASE_URL is not set and required DB_* variables are missing"
            )
        try:
            parsed_port = int(port)
        except ValueError:
            raise RuntimeError("DB_PORT must be a valid port") from None

        if not 1 <= parsed_port <= 65535:
            raise RuntimeError("DB_PORT must be between 1 and 65535")

        database_url = (
            f"postgresql://{quote(username, safe='')}:"
            f"{quote(password, safe='')}@{host}:{parsed_port}/"
            f"{quote(name, safe='')}"
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
