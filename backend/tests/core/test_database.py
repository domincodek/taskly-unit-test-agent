from app.core.database import create_database_engine
from unittest.mock import Mock, patch
from app.core.database import create_database_engine, create_session_factory, initialize


def test_engine_uses_the_postgresql_psycopg_driver():
    url = "postgresql+psycopg://taskly:taskly@localhost:5432/taskly"
    engine = create_database_engine(url)
    try:
        assert engine.url.drivername == "postgresql+psycopg"
        assert engine.dialect.name == "postgresql"
        assert engine.dialect.driver == "psycopg"
        assert engine.url.database == "taskly"
    finally:
        engine.dispose()

def test_session_factory_keeps_objects_loaded_after_commit():
    engine = create_database_engine("postgresql+psycopg://taskly:taskly@localhost:5432/taskly")
    try:
        factory = create_session_factory(engine)
        assert factory.kw["expire_on_commit"] is False
        assert factory.kw["bind"] is engine
    finally:
        engine.dispose()


def test_initialize_creates_tables_for_the_engine():
    engine = Mock()
    with patch("app.core.database.Base") as base:
        initialize(engine)
    base.metadata.create_all.assert_called_once_with(engine)
