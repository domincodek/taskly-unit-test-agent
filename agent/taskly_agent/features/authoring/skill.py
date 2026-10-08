from pathlib import Path

from ...domain.models import AgentState, AuthoredFile, RunContext
from .guard import assert_test_path
from .merge import MARKER_PYTHON, MARKER_TYPESCRIPT, merge
from . import python_patterns, python_pure, typescript_patterns, typescript_pure


def execute(state: AgentState, context: RunContext) -> tuple[str, tuple[AuthoredFile, ...]]:
    root = Path(context.root)
    authored: list[AuthoredFile] = []
    for target in state.assessment.targets:
        source = (root / target.source_path).read_text(encoding="utf-8")
        destination = root / target.test_path
        existing = destination.read_text(encoding="utf-8") if destination.exists() else None
        language = "python" if target.source_path.endswith(".py") else "typescript"
        owned = existing is not None and (MARKER_PYTHON in existing or MARKER_TYPESCRIPT in existing)
        pieces = collect_pieces(root, target.source_path, source, "" if owned else (existing or ""), language)
        updated = merge(existing, pieces, language)
        if updated is None or updated == existing:
            authored.append(AuthoredFile(target.test_path, "unchanged", "No safe test update."))
            continue
        output = assert_test_path(root, target.test_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(updated, encoding="utf-8", newline="\n")
        action = "created" if existing is None else "updated"
        authored.append(AuthoredFile(target.test_path, action, target.reason))
    written = [item for item in authored if item.action in {"created", "updated"}]
    if not state.assessment.targets:
        summary = "There were no units that needed new tests."
    elif not written:
        summary = "No supported unit could be updated safely."
    else:
        summary = f"Wrote {len(written)} test file(s)."
    return summary, tuple(authored)


def collect_pieces(root: Path, source_path: str, source: str, test_text: str, language: str):
    if language == "python":
        pieces = [
            *python_patterns.pieces_for(source_path, source, test_text),
            *python_pure.pieces_for(root, source_path, source, test_text),
        ]
    else:
        pieces = [
            *typescript_patterns.pieces_for(root, source_path, source, test_text),
            *typescript_pure.pieces_for(root, source_path, source, test_text),
        ]
    unique = []
    seen = set()
    for piece in pieces:
        if piece.name in seen:
            continue
        seen.add(piece.name)
        unique.append(piece)
    return unique
