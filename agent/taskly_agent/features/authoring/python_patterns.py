import re
import textwrap

from .merge import Piece
from .paths import module_name


def pieces_for(source_path: str, source: str, test_text: str) -> list[Piece]:
    if not source_path.endswith(".py"):
        return []
    pieces = [
        health_piece(source_path, source),
        config_piece(source_path, source),
        lifespan_piece(source_path, source),
        factory_piece(source_path, source),
        database_piece(source_path, source),
        dependency_piece(source_path, source),
    ]
    return [piece for piece in pieces if piece and f"def {piece.name}(" not in test_text]


def health_piece(source_path: str, source: str) -> Piece | None:
    if "def health" not in source or "APIRouter" not in source:
        return None
    prefix = _group(r'APIRouter\(prefix="([^"]*)"', source) or ""
    route = _group(r'@router\.get\("([^"]*)"', source) or "/health"
    status = _group(r'return\s*\{\s*"status"\s*:\s*"([^"]+)"', source) or "ok"
    module = module_name(source_path)
    body = textwrap.dedent(
        f"""
        def _health_client(repository):
            app = FastAPI()
            app.include_router(router)
            app.dependency_overrides[get_repository] = lambda: repository
            return TestClient(app)


        def test_health_reports_ok_when_the_database_answers():
            repository = Mock()
            with _health_client(repository) as client:
                response = client.get("{prefix}{route}")
            assert response.status_code == 200
            assert response.json() == {{"status": "{status}"}}
            repository.session.execute.assert_called_once()


        def test_health_surfaces_a_database_failure():
            repository = Mock()
            repository.session.execute.side_effect = RuntimeError("database unavailable")
            with _health_client(repository) as client:
                with pytest.raises(RuntimeError, match="database unavailable"):
                    client.get("{prefix}{route}")
        """
    ).strip()
    return Piece(
        "test_health_reports_ok_when_the_database_answers",
        body,
        (
            "from unittest.mock import Mock",
            "import pytest",
            "from fastapi import FastAPI",
            "from fastapi.testclient import TestClient",
            f"from {module} import router",
            "from app.api.dependencies import get_repository",
        ),
    )


def config_piece(source_path: str, source: str) -> Piece | None:
    required = ("POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_HOST", "DB_PORT", "POSTGRES_DB")
    if "def resolve_database_url" not in source or any(key not in source for key in required):
        return None
    module = module_name(source_path)
    body = textwrap.dedent(
        f"""
        def test_resolve_database_url_prefers_an_explicit_value(monkeypatch):
            with patch("{module}.load_dotenv"):
                monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://from-env/db")
                assert (
                    resolve_database_url("postgresql+psycopg://explicit/db")
                    == "postgresql+psycopg://explicit/db"
                )


        def test_resolve_database_url_reads_the_environment_variable(monkeypatch):
            with patch("{module}.load_dotenv"):
                monkeypatch.delenv("DATABASE_URL", raising=False)
                monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://from-env/db")
                assert resolve_database_url() == "postgresql+psycopg://from-env/db"


        def test_resolve_database_url_builds_a_postgres_url(monkeypatch):
            with patch("{module}.load_dotenv"):
                monkeypatch.delenv("DATABASE_URL", raising=False)
                for key, value in {{
                    "POSTGRES_USER": "taskly",
                    "POSTGRES_PASSWORD": "secret",
                    "POSTGRES_HOST": "db.internal",
                    "DB_PORT": "5432",
                    "POSTGRES_DB": "taskly",
                }}.items():
                    monkeypatch.setenv(key, value)
                assert (
                    resolve_database_url()
                    == "postgresql+psycopg://taskly:secret@db.internal:5432/taskly"
                )


        def test_resolve_database_url_requires_postgres_settings(monkeypatch):
            with patch("{module}.load_dotenv"):
                monkeypatch.delenv("DATABASE_URL", raising=False)
                for key in {required!r}:
                    monkeypatch.delenv(key, raising=False)
                with pytest.raises(KeyError):
                    resolve_database_url()
        """
    ).strip()
    return Piece(
        "test_resolve_database_url_prefers_an_explicit_value",
        body,
        (
            "from unittest.mock import patch",
            "import pytest",
            f"from {module} import resolve_database_url",
        ),
    )


def lifespan_piece(source_path: str, source: str) -> Piece | None:
    if "async def lifespan" not in source or "engine.dispose" not in source:
        return None
    module = module_name(source_path)
    body = textwrap.dedent(
        f"""
        def test_lifespan_prepares_sessions_and_disposes_the_engine():
            engine = Mock()
            factory = Mock()
            app = Mock()

            async def scenario():
                with (
                    patch("{module}.create_database_engine", return_value=engine) as create_engine,
                    patch("{module}.initialize") as initialize,
                    patch("{module}.create_session_factory", return_value=factory) as create_factory,
                ):
                    async with lifespan(app):
                        create_engine.assert_called_once_with(app.state.database_url)
                        initialize.assert_called_once_with(engine)
                        create_factory.assert_called_once_with(engine)
                        assert app.state.session_factory is factory
                    engine.dispose.assert_called_once_with()

            asyncio.run(scenario())


        def test_lifespan_disposes_the_engine_when_startup_fails():
            engine = Mock()
            app = Mock()

            async def scenario():
                with (
                    patch("{module}.create_database_engine", return_value=engine),
                    patch("{module}.initialize", side_effect=RuntimeError("schema")),
                    patch("{module}.create_session_factory"),
                ):
                    with pytest.raises(RuntimeError, match="schema"):
                        async with lifespan(app):
                            pass
                    engine.dispose.assert_called_once_with()

            asyncio.run(scenario())
        """
    ).strip()
    return Piece(
        "test_lifespan_prepares_sessions_and_disposes_the_engine",
        body,
        (
            "import asyncio",
            "from unittest.mock import Mock, patch",
            "import pytest",
            f"from {module} import lifespan",
        ),
    )


def factory_piece(source_path: str, source: str) -> Piece | None:
    if "def create_app" not in source or "FastAPI(" not in source:
        return None
    module = module_name(source_path)
    body = textwrap.dedent(
        """
        def test_create_app_publishes_routes_and_the_database_url():
            url = "postgresql+psycopg://taskly:taskly@localhost:5432/taskly"
            app = create_app(url)
            assert app.state.database_url == url
            paths = set()

            def collect(routes):
                for route in routes:
                    path = getattr(route, "path", None)
                    if isinstance(path, str):
                        paths.add(path)
                    original = getattr(route, "original_router", None)
                    if original is not None:
                        collect(original.routes)

            collect(app.routes)
            assert "/api/health" in paths
            assert any(path.startswith("/api/todos") for path in paths)
        """
    ).strip()
    return Piece("test_create_app_publishes_routes_and_the_database_url", body, (f"from {module} import create_app",))


def database_piece(source_path: str, source: str) -> Piece | None:
    if "def create_session_factory" not in source or "def initialize" not in source:
        return None
    module = module_name(source_path)
    body = textwrap.dedent(
        f"""
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
            with patch("{module}.Base") as base:
                initialize(engine)
            base.metadata.create_all.assert_called_once_with(engine)
        """
    ).strip()
    return Piece(
        "test_session_factory_keeps_objects_loaded_after_commit",
        body,
        (
            "from unittest.mock import Mock, patch",
            f"from {module} import create_database_engine, create_session_factory, initialize",
        ),
    )


def dependency_piece(source_path: str, source: str) -> Piece | None:
    if "session.rollback" not in source or "session.close" not in source or "yield " not in source:
        return None
    module = module_name(source_path)
    yielded = re.search(r"yield\s+(\w+)\(", source)
    repository = yielded.group(1) if yielded else "TodoRepository"
    imported = re.search(rf"from (\S+) import (?:\w+\s*,\s*)*{repository}\b", source)
    repository_module = "app.features.todos.repository"
    if imported and imported.group(1).startswith("."):
        relative = imported.group(1)
        dot_count = len(relative) - len(relative.lstrip("."))
        parent = module.split(".")[:-dot_count]
        remainder = [part for part in relative.lstrip(".").split(".") if part]
        repository_module = ".".join([*parent, *remainder])
    function = "get_repository"
    found = re.search(r"def (\w+)\(", source)
    if found:
        function = found.group(1)
    body = textwrap.dedent(
        f"""
        def _repository_dependency(session):
            app = SimpleNamespace(state=SimpleNamespace(session_factory=Mock(return_value=session)))
            request = Request({{"type": "http", "app": app}})
            return {function}(request)


        def test_repository_dependency_closes_the_session():
            session = Mock()
            dependency = _repository_dependency(session)
            repository = next(dependency)
            assert isinstance(repository, {repository})
            with pytest.raises(StopIteration):
                next(dependency)
            session.close.assert_called_once()
            session.rollback.assert_not_called()


        def test_repository_dependency_rolls_back_when_the_request_fails():
            session = Mock()
            dependency = _repository_dependency(session)
            next(dependency)
            with pytest.raises(RuntimeError, match="request failed"):
                dependency.throw(RuntimeError("request failed"))
            session.rollback.assert_called_once()
            session.close.assert_called_once()
        """
    ).strip()
    return Piece(
        "test_repository_dependency_closes_the_session",
        body,
        (
            "from types import SimpleNamespace",
            "from unittest.mock import Mock",
            "import pytest",
            "from starlette.requests import Request",
            f"from {module} import {function}",
            f"from {repository_module} import {repository}",
        ),
    )


def _group(pattern: str, source: str) -> str | None:
    found = re.search(pattern, source)
    if not found:
        return None
    return found.group(1)
