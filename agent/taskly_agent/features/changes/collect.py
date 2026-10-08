import subprocess
from pathlib import Path

from ...domain.models import ChangeSet, ChangedFile
from ..assessment.rules import is_test_candidate

SKIP_DIRS = {
    ".git",
    ".venv",
    "node_modules",
    "dist",
    "coverage",
    "storybook-static",
    "__pycache__",
    ".pytest_cache",
}


def collect_changes(root: Path, scope: str, base: str | None, head: str | None) -> ChangeSet:
    if scope == "gaps":
        files = tuple(
            ChangedFile(path, "A") for path in discover_sources(root)
        )
        return ChangeSet(files, base or "workspace", head or "workspace", scope)
    if scope == "pull-request":
        if not base or not head:
            raise ValueError("Pull request scope requires a base and a head revision.")
        files = tuple(parse_name_status(git_lines(root, ["diff", "--name-status", "--find-renames", base, head])))
        return ChangeSet(files, base, head, scope)
    if scope == "working-tree":
        baseline = base or "HEAD"
        tracked = parse_name_status(git_lines(root, ["diff", "--name-status", "--find-renames", baseline]))
        untracked = [
            ChangedFile(path, "A")
            for path in git_lines(root, ["ls-files", "--others", "--exclude-standard"])
            if path
        ]
        return ChangeSet(tuple([*tracked, *untracked]), baseline, "working-tree", scope)
    raise ValueError(f"Unsupported scope: {scope}")


def discover_sources(root: Path) -> list[str]:
    found: list[str] = []
    for relative_root in (Path("backend/app"), Path("frontend/src")):
        directory = root / relative_root
        if not directory.exists():
            continue
        for path in directory.rglob("*"):
            if not path.is_file() or any(part in SKIP_DIRS for part in path.parts):
                continue
            relative = path.relative_to(root).as_posix()
            if is_test_candidate(relative):
                found.append(relative)
    return sorted(found)


def git_lines(root: Path, args: list[str]) -> list[str]:
    completed = subprocess.run(
        ["git", *args],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(f"git {' '.join(args)} failed: {detail}")
    return [line.strip() for line in completed.stdout.splitlines() if line.strip()]


def parse_name_status(lines: list[str]) -> list[ChangedFile]:
    files: list[ChangedFile] = []
    for line in lines:
        parts = line.split("\t")
        status = parts[0]
        if status.startswith("R") or status.startswith("C"):
            files.append(ChangedFile(parts[2], "A"))
            continue
        if status[:1] not in {"A", "M", "D"}:
            continue
        files.append(ChangedFile(parts[1], status[:1]))
    return files
