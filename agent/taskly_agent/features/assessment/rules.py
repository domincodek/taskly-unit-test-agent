import ast
import re
from pathlib import Path

SOURCE_PREFIXES = ("backend/app/", "frontend/src/")
IGNORED_PARTS = (
    "/design-system/",
    "/__pycache__/",
)
IGNORED_SUFFIXES = (
    ".d.ts",
    ".stories.ts",
    ".stories.tsx",
)
IGNORED_NAMES = {
    "backend/app/main.py",
    "frontend/src/main.tsx",
    "frontend/src/lib/queryClient.ts",
}
IGNORED_FILE_NAMES = {
    "__init__.py",
    "schemas.py",
    "models.py",
    "types.py",
    "constants.ts",
    "constants.tsx",
    "index.ts",
    "index.tsx",
    "queryKeys.ts",
}


def is_test_file(path: str) -> bool:
    name = Path(path).name
    return (
        path.startswith("backend/tests/")
        or name.endswith(".test.ts")
        or name.endswith(".test.tsx")
        or name.endswith("_test.py")
        or name.startswith("test_")
    )


def is_test_candidate(path: str) -> bool:
    if not path.startswith(SOURCE_PREFIXES):
        return False
    if is_test_file(path):
        return False
    if path in IGNORED_NAMES:
        return False
    name = Path(path).name
    if name in IGNORED_FILE_NAMES or name.endswith(".types.ts"):
        return False
    if any(part in f"/{path}" for part in IGNORED_PARTS):
        return False
    if path.endswith(IGNORED_SUFFIXES):
        return False
    return path.endswith((".py", ".ts", ".tsx"))


def test_path_for(source_path: str) -> str | None:
    if not is_test_candidate(source_path):
        return None
    path = Path(source_path)
    if source_path.endswith(".py"):
        relative = Path(source_path).relative_to("backend/app")
        return (Path("backend/tests") / relative.parent / f"test_{relative.name}").as_posix()
    suffix = ".test.tsx" if source_path.endswith(".tsx") else ".test.ts"
    return path.with_suffix(suffix).as_posix()


def python_functions(source: str, test_exists: bool = False) -> list[str]:
    tree = ast.parse(source)
    names = []
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.name.startswith("_"):
            continue
        if node.decorator_list and test_exists:
            continue
        names.append(node.name)
    return names


def typescript_functions(source: str) -> list[str]:
    return re.findall(r"export (?:async )?function (\w+)", source)


def needs_tests(source_path: str, source: str, test_text: str) -> str | None:
    if (
        '__agent__ = "taskly-unit-test-agent"' in test_text
        or "const agentTestOwner = 'taskly-unit-test-agent'" in test_text
    ):
        return "refresh tests owned by the unit test agent"
    if source_path.endswith(".py"):
        for name in python_functions(source, bool(test_text)):
            if name not in test_text:
                return f"{name} has no test referencing it"
        for token, needle in (
            ("session.rollback", "rollback"),
            ("engine.dispose", "dispose"),
            ("def initialize", "initialize"),
            ("def create_session_factory", "create_session_factory"),
        ):
            if token in source and needle not in test_text:
                return f"{token} is not covered"
        return None
    for name in typescript_functions(source):
        if name not in test_text:
            return f"{name} has no test referencing it"
    return None
