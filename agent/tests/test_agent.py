import json
from pathlib import Path

import pytest

from taskly_agent.domain.models import AgentState, Assessment, ChangeSet, ChangedFile, RunContext, UnitTarget
from taskly_agent.features.authoring.guard import assert_test_path
from taskly_agent.features.authoring.merge import MARKER_PYTHON, Piece, merge
from taskly_agent.features.changes.collect import parse_name_status
from taskly_agent.features.publishing.comment import render_comment
from taskly_agent.orchestration.loop import run_agent
from taskly_agent.orchestration.policy import next_skill


def test_policy_follows_the_authoring_path():
    state = AgentState()
    assert next_skill(state) == "analyze-changes"
    state.changes = ChangeSet((), "base", "head", "pull-request")
    assert next_skill(state) == "assess-test-need"
    state.assessment = Assessment("author", "Create tests.", (UnitTarget("a.py", "backend/tests/test_a.py", "missing"),), (), ())
    assert next_skill(state) == "author-unit-tests"
    state.authored = ()
    assert next_skill(state) == "run-unit-tests"


def test_policy_publishes_a_skip_without_writing_tests():
    state = AgentState()
    state.changes = ChangeSet((), "base", "head", "pull-request")
    state.assessment = Assessment("skip", "No application code in this change needs a new unit test.", (), (), ())
    assert next_skill(state) == "publish-pr-results"


def test_guard_rejects_application_code(tmp_path: Path):
    with pytest.raises(PermissionError):
        assert_test_path(tmp_path, "backend/app/main.py")
    with pytest.raises(PermissionError):
        assert_test_path(tmp_path, "backend/tests/../../backend/app/main.py")


def test_guard_allows_a_backend_test(tmp_path: Path):
    target = assert_test_path(tmp_path, "backend/tests/features/test_progress.py")
    assert target == (tmp_path / "backend/tests/features/test_progress.py").resolve()


def test_diff_parser_keeps_renames_as_additions():
    files = parse_name_status(
        [
            "M\tbackend/app/features/todos/progress.py",
            "D\tREADME.md",
            "R100\told.py\tbackend/app/features/todos/progress.py",
        ]
    )
    assert [item.status for item in files] == ["M", "D", "A"]
    assert files[2].path == "backend/app/features/todos/progress.py"


def test_merge_appends_without_replacing_a_human_test():
    existing = "def test_human():\n    assert True\n"
    updated = merge(
        existing,
        [Piece("test_added", "def test_added():\n    assert 1 == 1\n", ("import pytest",))],
        "python",
    )
    assert "def test_human" in updated
    assert "def test_added" in updated
    assert MARKER_PYTHON not in updated


def test_comment_marks_the_pull_request_note():
    state = AgentState()
    state.assessment = Assessment("skip", "No application code in this change needs a new unit test.", (), (), ())
    state.published = True
    comment = render_comment(state)
    assert comment.startswith("<!-- taskly-unit-test-agent -->")
    assert "No application code" in comment


def test_agent_characterizes_a_pure_function_and_runs_the_test(tmp_path: Path):
    module = tmp_path / "backend" / "app" / "features" / "stats"
    module.mkdir(parents=True)
    (module / "progress.py").write_text(
        "def remaining_count(completed: list[bool]) -> int:\n"
        "    return sum(1 for item in completed if not item)\n",
        encoding="utf-8",
    )
    write_skills(tmp_path)
    state = run_agent(RunContext(str(tmp_path), "gaps", None, None, None, None, None))
    test_file = tmp_path / "backend" / "tests" / "features" / "stats" / "test_progress.py"
    assert test_file.exists()
    assert "remaining_count([]) == 0" in test_file.read_text(encoding="utf-8")
    assert state.verification is not None
    assert state.verification.passed
    report = json.loads((tmp_path / "agent" / "reports" / "result.json").read_text(encoding="utf-8"))
    assert report["passed"] is True
    assert [item["name"] for item in report["skills"]][0] == "analyze-changes"


def write_skills(root: Path):
    names = {
        "analyze-changes": "Reads a pull request diff and lists changed application files.",
        "assess-test-need": "Decides whether changed application code needs new or updated unit tests.",
        "author-unit-tests": "Creates or updates unit tests for frontend and backend changes.",
        "run-unit-tests": "Runs the affected pytest and Vitest files and records the result.",
        "repair-unit-tests": "Runs the affected tests one more time after a failure.",
        "publish-pr-results": "Publishes the agent decision and test results on the pull request.",
    }
    for name, description in names.items():
        directory = root / ".cursor" / "skills" / name
        directory.mkdir(parents=True)
        (directory / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: {description}\n---\n\n# {name}\n",
            encoding="utf-8",
        )
