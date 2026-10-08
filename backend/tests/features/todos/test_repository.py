from datetime import datetime, timezone
from unittest.mock import Mock, patch

from sqlalchemy import select
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Session

from app.features.todos.models import TodoRecord
from app.features.todos.repository import TodoRepository
from app.features.todos.schemas import TodoCreate, TodoUpdate


def test_list_maps_models_and_orders_tasks_newest_first(model_factory, todo_values, todo):
    session = Mock(spec=Session)
    session.scalars.return_value = [model_factory(todo_values)]
    assert TodoRepository(session).list() == [todo]
    statement = session.scalars.call_args.args[0]
    expected = select(TodoRecord).order_by(TodoRecord.created_at.desc(), TodoRecord.id.desc())
    assert statement.compare(expected)
    compiled = str(statement.compile(dialect=postgresql.dialect()))
    assert "ORDER BY todos.created_at DESC, todos.id DESC" in compiled


def test_get_returns_none_for_missing_task():
    session = Mock(spec=Session)
    session.get.return_value = None
    assert TodoRepository(session).get(404) is None
    session.get.assert_called_once_with(TodoRecord, 404)


def test_get_maps_a_stored_task(model_factory, todo_values, todo):
    session = Mock(spec=Session)
    session.get.return_value = model_factory(todo_values)
    assert TodoRepository(session).get(todo_values["id"]) == todo


def test_create_persists_and_maps_the_new_task(todo):
    session = Mock(spec=Session)
    moment = datetime(2026, 10, 8, 12, tzinfo=timezone.utc)

    def stamp(record):
        record.id = todo.id

    session.refresh.side_effect = stamp
    with patch("app.features.todos.repository.datetime") as clock:
        clock.now.return_value = moment
        saved = TodoRepository(session).create(TodoCreate(title="Plan the sprint", priority="high"))
    record = session.add.call_args.args[0]
    assert record.title == "Plan the sprint"
    assert record.priority == "high"
    assert record.created_at == moment
    assert record.updated_at == moment
    session.commit.assert_called_once_with()
    assert saved.title == "Plan the sprint"
    assert saved.id == todo.id


def test_update_returns_none_when_the_task_is_missing():
    session = Mock(spec=Session)
    session.get.return_value = None
    assert TodoRepository(session).update(4, TodoUpdate(title="Renamed")) is None
    session.commit.assert_not_called()


def test_update_writes_the_provided_fields(model_factory, todo_values, todo):
    session = Mock(spec=Session)
    record = model_factory(todo_values)
    session.get.return_value = record
    moment = datetime(2026, 10, 8, 15, tzinfo=timezone.utc)
    with patch("app.features.todos.repository.datetime") as clock:
        clock.now.return_value = moment
        saved = TodoRepository(session).update(todo_values["id"], TodoUpdate(title="Renamed"))
    assert record.title == "Renamed"
    assert record.updated_at == moment
    session.commit.assert_called_once_with()
    assert saved.title == "Renamed"
    assert saved.id == todo.id


def test_delete_removes_a_stored_task(model_factory, todo_values):
    session = Mock(spec=Session)
    record = model_factory(todo_values)
    session.get.return_value = record
    assert TodoRepository(session).delete(todo_values["id"]) is True
    session.delete.assert_called_once_with(record)
    session.commit.assert_called_once_with()


def test_delete_returns_false_when_the_task_is_missing():
    session = Mock(spec=Session)
    session.get.return_value = None
    assert TodoRepository(session).delete(4) is False
    session.delete.assert_not_called()
