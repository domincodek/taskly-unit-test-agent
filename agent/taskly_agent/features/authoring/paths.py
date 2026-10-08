import os
from pathlib import Path


def module_name(source_path: str) -> str:
    relative = source_path.removeprefix("backend/").removesuffix(".py")
    return relative.replace("/", ".")


def relative_import(from_file: str, target_file: str) -> str:
    source_dir = Path(from_file).parent
    target = Path(target_file).with_suffix("")
    relative = Path(os.path.relpath(target, source_dir)).as_posix()
    if not relative.startswith("."):
        relative = f"./{relative}"
    return relative


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")
