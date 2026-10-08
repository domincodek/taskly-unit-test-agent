__agent__ = "taskly-unit-test-agent"

from unittest.mock import patch

import pytest

from app.core.config import resolve_database_url

def test_resolve_database_url_prefers_an_explicit_value(monkeypatch):
    with patch("app.core.config.load_dotenv"):
        monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://from-env/db")
        assert (
            resolve_database_url("postgresql+psycopg://explicit/db")
            == "postgresql+psycopg://explicit/db"
        )


def test_resolve_database_url_reads_the_environment_variable(monkeypatch):
    with patch("app.core.config.load_dotenv"):
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://from-env/db")
        assert resolve_database_url() == "postgresql+psycopg://from-env/db"


def test_resolve_database_url_builds_a_postgres_url(monkeypatch):
    with patch("app.core.config.load_dotenv"):
        monkeypatch.delenv("DATABASE_URL", raising=False)
        for key, value in {
            "POSTGRES_USER": "taskly",
            "POSTGRES_PASSWORD": "secret",
            "POSTGRES_HOST": "db.internal",
            "DB_PORT": "5432",
            "POSTGRES_DB": "taskly",
        }.items():
            monkeypatch.setenv(key, value)
        assert (
            resolve_database_url()
            == "postgresql+psycopg://taskly:secret@db.internal:5432/taskly"
        )


def test_resolve_database_url_requires_postgres_settings(monkeypatch):
    with patch("app.core.config.load_dotenv"):
        monkeypatch.delenv("DATABASE_URL", raising=False)
        for key in ('POSTGRES_USER', 'POSTGRES_PASSWORD', 'POSTGRES_HOST', 'DB_PORT', 'POSTGRES_DB'):
            monkeypatch.delenv(key, raising=False)
        with pytest.raises(KeyError):
            resolve_database_url()
