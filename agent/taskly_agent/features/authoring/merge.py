from dataclasses import dataclass


@dataclass(frozen=True)
class Piece:
    name: str
    body: str
    imports: tuple[str, ...]


MARKER_PYTHON = '__agent__ = "taskly-unit-test-agent"'
MARKER_TYPESCRIPT = "const agentTestOwner = 'taskly-unit-test-agent'"


def merge(existing: str | None, pieces: list[Piece], language: str) -> str | None:
    if not pieces:
        return existing
    marker = MARKER_PYTHON if language == "python" else MARKER_TYPESCRIPT
    owned = existing is not None and marker in existing
    if existing is None or owned:
        return render(pieces, language, owned=True)
    missing = [piece for piece in pieces if piece.name not in existing]
    if not missing:
        return existing
    updated = add_imports(existing, [line for piece in missing for line in piece.imports])
    addition = "\n\n".join(piece.body.strip() for piece in missing)
    return updated.rstrip() + "\n\n" + addition + "\n"


def render(pieces: list[Piece], language: str, owned: bool) -> str:
    marker = MARKER_PYTHON if language == "python" else MARKER_TYPESCRIPT
    imports = group_imports(dedupe_imports([line for piece in pieces for line in piece.imports]))
    bodies = "\n\n".join(piece.body.strip() for piece in pieces if piece.body.strip())
    if language == "python":
        chunks = ([marker, ""] if owned else []) + [*imports, "", bodies, ""]
    else:
        chunks = [*imports, ""] + ([marker, ""] if owned else []) + [bodies, ""]
    return "\n".join(chunks).lstrip("\n")


def dedupe_imports(lines: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for line in lines:
        if not line or line in seen:
            continue
        seen.add(line)
        ordered.append(line)
    return ordered


def group_imports(lines: list[str]) -> list[str]:
    buckets = {0: [], 1: [], 2: []}
    for line in lines:
        buckets[import_rank(line)].append(line)
    grouped: list[str] = []
    for rank in (0, 1, 2):
        if not buckets[rank]:
            continue
        if grouped:
            grouped.append("")
        grouped.extend(buckets[rank])
    return grouped


def import_rank(line: str) -> int:
    module = line.removeprefix("from ").removeprefix("import ").split(" ")[0].split(".")[0]
    if module in {"app"} or line.startswith("from './") or line.startswith("from '../") or line.startswith('from "./') or line.startswith('from "../'):
        return 2
    if module in {"pytest", "fastapi", "starlette", "pydantic", "sqlalchemy", "vitest"}:
        return 1
    if line.startswith("import {") or line.startswith("import type"):
        return 2 if "from '" in line and ("./" in line or "../" in line) else 1
    return 0


def add_imports(source: str, lines: list[str]) -> str:
    missing = [line for line in dedupe_imports(lines) if line not in source]
    if not missing:
        return source if source.endswith("\n") else source + "\n"
    rows = source.splitlines()
    insert_at = 0
    for index, row in enumerate(rows):
        if row.startswith(("import ", "from ", "import{")) or row.startswith("import {"):
            insert_at = index + 1
    for offset, line in enumerate(missing):
        rows.insert(insert_at + offset, line)
    text = "\n".join(rows)
    return text + "\n"
