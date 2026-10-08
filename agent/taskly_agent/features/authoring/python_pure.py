import ast
import json
import subprocess
import sys
from pathlib import Path

from ...runtime import child_env
from .merge import Piece
from .paths import module_name

SIDE_EFFECTS = (
    "os.environ",
    "os.getenv",
    "load_dotenv",
    "open(",
    "subprocess",
    "socket",
    "session",
    "create_engine",
    "fetch(",
    "print(",
)


def pieces_for(root: Path, source_path: str, source: str, test_text: str) -> list[Piece]:
    if not source_path.endswith(".py"):
        return []
    tree = ast.parse(source)
    selected = []
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef) or node.name.startswith("_") or node.decorator_list:
            continue
        if node.name in test_text:
            continue
        segment = ast.get_source_segment(source, node) or ""
        if any(token in segment for token in SIDE_EFFECTS):
            continue
        sample_sets = parameter_samples(node)
        if sample_sets is None:
            continue
        selected.append((node.name, sample_sets))
    if not selected:
        return []
    cases = []
    for name, sample_sets in selected:
        for index, args in enumerate(case_matrix(sample_sets)):
            cases.append(
                {
                    "id": f"{name}-{index}",
                    "function": name,
                    "args": args,
                    "arg_repr": [repr(arg) for arg in args],
                    "index": index,
                }
            )
    results = execute(root, module_name(source_path), cases)
    grouped: dict[str, list[dict]] = {}
    by_id = {item["id"]: item for item in results}
    for case in cases:
        result = by_id.get(case["id"])
        if not result or not result.get("ok"):
            continue
        rendered = result.get("repr", "")
        if not isinstance(rendered, str) or rendered.startswith("<"):
            continue
        grouped.setdefault(case["function"], []).append({**case, "repr": rendered})
    if not grouped:
        return []
    import_line = f"from {module_name(source_path)} import {', '.join(grouped)}"
    pieces: list[Piece] = []
    for name, items in grouped.items():
        for item in items:
            call = ", ".join(item["arg_repr"])
            pieces.append(
                Piece(
                    name=f"test_{name}_case_{item['index']}",
                    body=(
                        f"def test_{name}_case_{item['index']}():\n"
                        f"    assert {name}({call}) == {item['repr']}\n"
                    ),
                    imports=(import_line,),
                )
            )
    return pieces


def parameter_samples(node: ast.FunctionDef) -> list[list[object]] | None:
    if node.args.vararg or node.args.kwarg or node.args.kwonlyargs or len(node.args.args) > 4:
        return None
    sample_sets = []
    for arg in node.args.args:
        samples = samples_for(annotation_kind(arg.annotation))
        if not samples:
            return None
        sample_sets.append(samples)
    return sample_sets


def annotation_kind(node: ast.expr | None):
    if node is None:
        return None
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Constant) and node.value is None:
        return "None"
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        return ("union", annotation_kind(node.left), annotation_kind(node.right))
    if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name) and node.value.id == "list":
        return ("list", annotation_kind(node.slice))
    return None


def samples_for(kind) -> list[object] | None:
    if kind == "str":
        return ["", "task"]
    if kind == "int":
        return [0, 1, -1]
    if kind == "float":
        return [0.0, 1.5]
    if kind == "bool":
        return [False, True]
    if kind == "None":
        return [None]
    if isinstance(kind, tuple) and kind[0] == "union":
        left, right = kind[1], kind[2]
        if "None" not in {left, right}:
            return None
        other = right if left == "None" else left
        other_samples = samples_for(other)
        if not other_samples:
            return None
        return [None, *other_samples]
    if isinstance(kind, tuple) and kind[0] == "list":
        inner = samples_for(kind[1])
        if not inner:
            return None
        return [[], [inner[0]], inner[:2]]
    return None


def case_matrix(sample_sets: list[list[object]]) -> list[list[object]]:
    if not sample_sets:
        return [[]]
    base = [samples[0] for samples in sample_sets]
    cases = [list(base)]
    for index, samples in enumerate(sample_sets):
        for sample in samples[1:]:
            variant = list(base)
            variant[index] = sample
            cases.append(variant)
            if len(cases) >= 6:
                return cases
    return cases


def execute(root: Path, module: str, cases: list[dict]) -> list[dict]:
    payload = {
        "module": module,
        "cases": [{"id": case["id"], "function": case["function"], "args": case["args"]} for case in cases],
    }
    script = """
import importlib, json, sys
payload = json.loads(sys.stdin.read())
module = importlib.import_module(payload["module"])
output = []
for case in payload["cases"]:
    try:
        value = getattr(module, case["function"])(*case["args"])
        output.append({"id": case["id"], "ok": True, "repr": repr(value)})
    except Exception as exc:
        output.append({"id": case["id"], "ok": False, "error": type(exc).__name__, "message": str(exc)})
json.dump(output, sys.stdout)
"""
    completed = subprocess.run(
        [sys.executable, "-c", script],
        input=json.dumps(payload),
        cwd=root / "backend",
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
        env=child_env({"PYTHONPATH": str((root / "backend").resolve())}),
    )
    if completed.returncode != 0 or not completed.stdout.strip():
        return []
    try:
        parsed = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []
