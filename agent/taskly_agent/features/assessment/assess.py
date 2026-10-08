from pathlib import Path

from ...domain.models import Assessment, ChangeSet, UnitTarget
from .rules import is_test_candidate, is_test_file, needs_tests, test_path_for


def assess(root: Path, changes: ChangeSet) -> Assessment:
    targets: list[UnitTarget] = []
    skipped: list[tuple[str, str]] = []
    verify: list[str] = []
    for changed in changes.files:
        if changed.status == "D":
            skipped.append((changed.path, "deleted files are not rewritten"))
            continue
        if is_test_file(changed.path):
            verify.append(changed.path)
            skipped.append((changed.path, "test file is executed, not regenerated"))
            continue
        if not is_test_candidate(changed.path):
            skipped.append((changed.path, "outside the unit-test boundary"))
            continue
        test_path = test_path_for(changed.path)
        if test_path is None:
            skipped.append((changed.path, "no test path mapping"))
            continue
        source = (root / changed.path).read_text(encoding="utf-8")
        test_file = root / test_path
        test_text = test_file.read_text(encoding="utf-8") if test_file.exists() else ""
        reason = needs_tests(changed.path, source, test_text)
        if reason is None:
            if test_file.exists():
                verify.append(test_path)
            skipped.append((changed.path, "existing tests already reference the changed units"))
            continue
        targets.append(UnitTarget(changed.path, test_path, reason))
        verify.append(test_path)
    if targets:
        action = "author"
        summary = f"Create or update tests for {len(targets)} changed unit(s)."
    elif verify:
        action = "verify"
        summary = "Changed code already has tests, so they will be run without rewriting them."
    else:
        action = "skip"
        summary = "No application code in this change needs a new unit test."
    return Assessment(action, summary, tuple(targets), tuple(skipped), tuple(dict.fromkeys(verify)))
