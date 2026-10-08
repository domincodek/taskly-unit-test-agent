import re
from pathlib import Path

ALLOWED = (
    re.compile(r"^backend/tests/.+\.py$"),
    re.compile(r"^frontend/src/.+\.test\.tsx?$"),
)


def assert_test_path(root: Path, relative: str) -> Path:
    normalized = relative.replace("\\", "/")
    if ".." in Path(normalized).parts or not any(pattern.fullmatch(normalized) for pattern in ALLOWED):
        raise PermissionError(f"Refusing to write outside the test sandbox: {relative}")
    root_resolved = root.resolve()
    target = (root_resolved / normalized).resolve()
    if not target.is_relative_to(root_resolved):
        raise PermissionError(f"Refusing to write outside the repository: {relative}")
    return target
