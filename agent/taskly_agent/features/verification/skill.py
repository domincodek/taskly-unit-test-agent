import os
import subprocess
import sys
from pathlib import Path

from ...domain.models import AgentState, CommandResult, RunContext, Verification
from ...runtime import child_env


def execute(state: AgentState, context: RunContext) -> tuple[str, Verification]:
    root = Path(context.root)
    paths = selected_paths(state, root)
    results: list[CommandResult] = []
    if any(path.startswith("backend/tests/") for path in paths):
        backend = [path for path in paths if path.startswith("backend/tests/")]
        results.append(
            run(
                root,
                [sys.executable, "-m", "pytest", *backend, "-q", "--tb=short"],
                {"PYTHONPATH": str((root / "backend").resolve())},
            )
        )
    frontend = [path for path in paths if path.startswith("frontend/src/")]
    if frontend:
        npm = "npm.cmd" if os.name == "nt" else "npm"
        relative = [str(Path(path).relative_to("frontend")).replace("\\", "/") for path in frontend]
        results.append(run(root / "frontend", [npm, "test", "--", *relative]))
    passed = all(item.code == 0 for item in results)
    if not results:
        summary = "No test files were available to run."
    elif passed:
        summary = f"Tests passed in {len(results)} command(s)."
    else:
        summary = "Tests failed."
    return summary, Verification(passed, tuple(results))


def selected_paths(state: AgentState, root: Path) -> list[str]:
    if state.authored:
        preferred = [item.path for item in state.authored if item.action in {"created", "updated"}]
        if preferred:
            return [path for path in preferred if (root / path).exists()]
    return [path for path in state.assessment.verify_paths if (root / path).exists()]


def run(cwd: Path, command: list[str], extra_env: dict[str, str] | None = None) -> CommandResult:
    completed = subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
        env=child_env(extra_env),
    )
    output = "\n".join(part for part in (completed.stdout, completed.stderr) if part).strip()
    rendered = " ".join(command)
    return CommandResult(rendered, completed.returncode, output[-6000:])
