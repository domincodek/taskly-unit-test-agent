__agent__ = "taskly-unit-test-agent"

import asyncio
from unittest.mock import Mock, patch

import pytest

from app.core.lifespan import lifespan

def test_lifespan_prepares_sessions_and_disposes_the_engine():
    engine = Mock()
    factory = Mock()
    app = Mock()

    async def scenario():
        with (
            patch("app.core.lifespan.create_database_engine", return_value=engine) as create_engine,
            patch("app.core.lifespan.initialize") as initialize,
            patch("app.core.lifespan.create_session_factory", return_value=factory) as create_factory,
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
            patch("app.core.lifespan.create_database_engine", return_value=engine),
            patch("app.core.lifespan.initialize", side_effect=RuntimeError("schema")),
            patch("app.core.lifespan.create_session_factory"),
        ):
            with pytest.raises(RuntimeError, match="schema"):
                async with lifespan(app):
                    pass
            engine.dispose.assert_called_once_with()

    asyncio.run(scenario())
