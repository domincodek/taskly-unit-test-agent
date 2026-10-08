__agent__ = "taskly-unit-test-agent"

from app.factory import create_app

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
