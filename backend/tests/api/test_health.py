__agent__ = "taskly-unit-test-agent"

from unittest.mock import Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.health import router
from app.api.dependencies import get_repository

def _health_client(repository):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_repository] = lambda: repository
    return TestClient(app)


def test_health_reports_ok_when_the_database_answers():
    repository = Mock()
    with _health_client(repository) as client:
        response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    repository.session.execute.assert_called_once()


def test_health_surfaces_a_database_failure():
    repository = Mock()
    repository.session.execute.side_effect = RuntimeError("database unavailable")
    with _health_client(repository) as client:
        with pytest.raises(RuntimeError, match="database unavailable"):
            client.get("/api/health")
