import pytest

from app.features.todos.schemas import TodoCreate


def test_list_returns_tasks_from_repository(client, repository_mock, todo):
    repository_mock.list.return_value = [todo]
    response = client.get("/api/todos")
    assert response.status_code == 200
    assert response.json() == [todo.model_dump(mode="json")]
    repository_mock.list.assert_called_once_with()


def test_create_trims_input_and_returns_created_task(client, repository_mock, todo):
    repository_mock.create.return_value = todo
    response = client.post("/api/todos", json={"title": "  Plan the sprint  ", "priority": "high"})
    assert response.status_code == 201
    assert response.json() == todo.model_dump(mode="json")
    repository_mock.create.assert_called_once_with(
        TodoCreate(title="Plan the sprint", priority="high")
    )


@pytest.mark.parametrize("payload", [
    {"title": "   "},
    {"title": "x" * 121},
    {"title": "Task", "priority": "urgent"},
    {"title": "Task", "due_date": "2026-02-30"},
])
def test_invalid_create_never_calls_repository(client, repository_mock, payload):
    assert client.post("/api/todos", json=payload).status_code == 422
    repository_mock.create.assert_not_called()


def test_get_returns_one_task(client, repository_mock, todo):
    repository_mock.get.return_value = todo
    response = client.get("/api/todos/7")
    assert response.status_code == 200
    assert response.json() == todo.model_dump(mode="json")
    repository_mock.get.assert_called_once_with(7)


def test_get_reports_an_unknown_task(client, repository_mock):
    repository_mock.get.return_value = None
    response = client.get("/api/todos/7")
    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found."


def test_update_returns_the_saved_task(client, repository_mock, todo):
    repository_mock.update.return_value = todo
    response = client.patch("/api/todos/7", json={"title": "Renamed"})
    assert response.status_code == 200
    assert response.json() == todo.model_dump(mode="json")
    todo_id, payload = repository_mock.update.call_args.args
    assert todo_id == 7
    assert payload.title == "Renamed"


def test_update_reports_an_unknown_task(client, repository_mock):
    repository_mock.update.return_value = None
    assert client.patch("/api/todos/7", json={"completed": True}).status_code == 404


def test_delete_returns_no_content(client, repository_mock):
    repository_mock.delete.return_value = True
    response = client.delete("/api/todos/7")
    assert response.status_code == 204
    assert response.content == b""
    repository_mock.delete.assert_called_once_with(7)


def test_delete_reports_an_unknown_task(client, repository_mock):
    repository_mock.delete.return_value = False
    assert client.delete("/api/todos/7").status_code == 404


def test_rejects_a_non_positive_task_id(client, repository_mock):
    assert client.get("/api/todos/0").status_code == 422
    repository_mock.get.assert_not_called()
