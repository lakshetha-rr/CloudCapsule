
import pytest

from app.database import get_database_url


@pytest.mark.parametrize(
    "database_url",
    [
        "",
        "mysql://user:pass@localhost/db",
        "postgresql://localhost",
        "postgresql://localhost:99999/db",
        "postgresql://localhost/db?unexpected=true",
        "postgresql://localhost/db#fragment",
    ],
)
def test_invalid_database_urls_are_rejected(monkeypatch, database_url):
    monkeypatch.setenv("DATABASE_URL", database_url)

    with pytest.raises(RuntimeError):
        get_database_url()


def test_missing_database_url_is_rejected(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(RuntimeError, match="not set"):
        get_database_url()


@pytest.mark.parametrize(
    "database_url",
    [
        "postgresql://user:pass@localhost:5432/cloudcapsule",
        "postgres://user:pass@localhost/cloudcapsule",
    ],
)
def test_valid_database_urls_are_accepted(monkeypatch, database_url):
    monkeypatch.setenv("DATABASE_URL", database_url)

    assert get_database_url() == database_url
