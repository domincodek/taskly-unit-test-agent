from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from starlette.requests import Request

from app.api.dependencies import get_repository
from app.features.todos.repository import TodoRepository


def test_session_creation_failure_propagates_from_repository_dependency():
    session_factory = Mock(side_effect=RuntimeError("Session unavailable"))
    app = SimpleNamespace(state=SimpleNamespace(session_factory=session_factory))
    request = Request({"type": "http", "app": app})
    dependency = get_repository(request)
    with pytest.raises(RuntimeError, match="Session unavailable"):
        next(dependency)
    session_factory.assert_called_once_with()

def _repository_dependency(session):
    app = SimpleNamespace(state=SimpleNamespace(session_factory=Mock(return_value=session)))
    request = Request({"type": "http", "app": app})
    return get_repository(request)


def test_repository_dependency_closes_the_session():
    session = Mock()
    dependency = _repository_dependency(session)
    repository = next(dependency)
    assert isinstance(repository, TodoRepository)
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
