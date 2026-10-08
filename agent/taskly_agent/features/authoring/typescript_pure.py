import json
import re
import subprocess
import tempfile
from pathlib import Path

from ...runtime import child_env
from .merge import Piece

PROBE = Path(__file__).with_name("probe.mjs")


def pieces_for(root: Path, source_path: str, source: str, test_text: str) -> list[Piece]:
    if not source_path.endswith(".ts") or source_path.endswith(".tsx"):
        return []
    aliases = load_aliases(root, source_path, source)
    selected = []
    for name, params, body in exported_functions(source):
        if name in test_text or "new Date()" in body:
            continue
        parsed = split_params(params)
        if parsed is None:
            continue
        sample_sets = []
        supported = True
        for param_name, annotation in parsed:
            samples = samples_for(annotation, aliases, param_name)
            if not samples:
                supported = False
                break
            sample_sets.append(samples)
        if not supported:
            continue
        selected.append((name, sample_sets))
    if not selected:
        return []
    cases = []
    for name, sample_sets in selected:
        for index, args in enumerate(case_matrix(sample_sets)):
            cases.append({"id": f"{name}-{index}", "function": name, "args": args, "index": index})
    results = execute(root / source_path, cases)
    by_id = {item["id"]: item for item in results}
    grouped: dict[str, list[dict]] = {}
    for case in cases:
        result = by_id.get(case["id"])
        if not result or not result.get("ok"):
            continue
        grouped.setdefault(case["function"], []).append({**case, **result})
    if not grouped:
        return []
    import_path = f"./{Path(source_path).stem}"
    import_line = f"import {{ {', '.join(grouped)} }} from '{import_path}'"
    pieces: list[Piece] = []
    for name, items in grouped.items():
        for item in items:
            call = ", ".join(to_ts(arg) for arg in item["args"])
            expected = "toBeUndefined()" if item.get("undefined") else f"toEqual({to_ts(item['value'])})"
            title = f"characterizes {name} for case {item['index']}"
            pieces.append(
                Piece(
                    title,
                    (
                        f"it('{title}', () => {{\n"
                        f"  expect({name}({call})).{expected}\n"
                        f"}})\n"
                    ),
                    ("import { expect, it } from 'vitest'", import_line),
                )
            )
    return pieces


def exported_functions(source: str) -> list[tuple[str, str, str]]:
    found = []
    for match in re.finditer(r"export (?:async )?function (\w+)\(", source):
        params, params_end = read_parens(source, match.end() - 1)
        brace = source.find("{", params_end)
        if brace < 0:
            continue
        body, _end = read_braces(source, brace)
        found.append((match.group(1), params, body))
    return found


def read_parens(source: str, start: int) -> tuple[str, int]:
    depth = 0
    for index in range(start, len(source)):
        if source[index] == "(":
            depth += 1
        elif source[index] == ")":
            depth -= 1
            if depth == 0:
                return source[start + 1 : index], index + 1
    return "", start


def read_braces(source: str, start: int) -> tuple[str, int]:
    depth = 0
    for index in range(start, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start : index + 1], index + 1
    return "", start


def split_params(params: str) -> list[tuple[str, str]] | None:
    if not params.strip():
        return []
    if "{" in params or "}" in params:
        return None
    parsed = []
    for chunk in params.split(","):
        if ":" not in chunk:
            return None
        name, annotation = chunk.split(":", 1)
        parsed.append((name.strip(), annotation.strip()))
    return parsed


def load_aliases(root: Path, source_path: str, source: str) -> dict:
    aliases = parse_aliases(source)
    for match in re.finditer(r"from '([^']+)'", source):
        candidate = resolve_spec(root, source_path, match.group(1))
        if candidate is None:
            continue
        aliases.update(parse_aliases(candidate.read_text(encoding="utf-8")))
    return aliases


def resolve_spec(root: Path, source_path: str, spec: str) -> Path | None:
    if not spec.startswith("."):
        return None
    base = (root / source_path).parent / spec
    for suffix in (".ts", ".tsx"):
        candidate = base.with_suffix(suffix) if base.suffix == "" else base
        if candidate.suffix not in {".ts", ".tsx"}:
            candidate = Path(str(base) + suffix)
        if candidate.exists():
            return candidate
    return None


def parse_aliases(source: str) -> dict:
    aliases: dict = {}
    for match in re.finditer(r"export type (\w+) = ([^\n]+)", source):
        aliases[match.group(1)] = match.group(2).strip().rstrip(";")
    for match in re.finditer(r"export interface (\w+)(?: extends (\w+))? \{([^}]*)\}", source, re.S):
        fields = {}
        for line in match.group(3).splitlines():
            cleaned = line.strip().rstrip(",")
            if ":" not in cleaned:
                continue
            name, annotation = cleaned.split(":", 1)
            fields[name.strip()] = annotation.strip()
        parent = match.group(2)
        if parent and isinstance(aliases.get(parent), dict):
            fields = {**aliases[parent], **fields}
        aliases[match.group(1)] = fields
    return aliases


def samples_for(annotation: str, aliases: dict, field_name: str = "", depth: int = 0):
    if depth > 6:
        return None
    annotation = annotation.strip()
    if field_name and "date" in field_name and annotation.replace(" ", "") in {"string|null", "null|string", "string"}:
        return [None, "2026-10-08", "not-a-date"] if "null" in annotation else ["2026-10-08", "not-a-date"]
    if annotation.endswith("[]"):
        inner = samples_for(annotation[:-2], aliases, depth=depth + 1)
        if not inner:
            return None
        return [[], [inner[0]], inner[:2]]
    if annotation.startswith("Array<") and annotation.endswith(">"):
        return samples_for(annotation[len("Array<") : -1] + "[]", aliases, field_name, depth + 1)
    if annotation in {"string"}:
        return ["task", "", "x" * 121, "x" * 2001]
    if annotation == "number":
        return [0, 1, -1]
    if annotation == "boolean":
        return [False, True]
    if annotation == "null":
        return [None]
    if re.fullmatch(r"(?:'[^']*'|\"[^\"]*\")(?:\s*\|\s*(?:'[^']*'|\"[^\"]*\"))+", annotation):
        return [part.strip().strip("'\"") for part in annotation.split("|")]
    if "|" in annotation:
        options = [part.strip() for part in annotation.split("|")]
        if "null" in options and len(options) == 2:
            other = next(part for part in options if part != "null")
            inner = samples_for(other, aliases, field_name, depth + 1)
            if not inner:
                return None
            return [None, *inner[:3]]
        return None
    aliased = aliases.get(annotation)
    if isinstance(aliased, dict):
        return object_samples(aliased, aliases)
    if isinstance(aliased, str):
        return samples_for(aliased, aliases, field_name, depth + 1)
    return None


def object_samples(fields: dict, aliases: dict) -> list[dict] | None:
    field_samples = {}
    for name, annotation in fields.items():
        samples = samples_for(annotation, aliases, name)
        if not samples:
            return None
        field_samples[name] = samples
    base = {name: samples[0] for name, samples in field_samples.items()}
    variants = [base]
    for name, samples in field_samples.items():
        picks = samples[1:3]
        for sample in picks:
            variant = dict(base)
            variant[name] = sample
            variants.append(variant)
            if len(variants) >= 10:
                return variants
    return variants


def case_matrix(sample_sets: list[list]) -> list[list]:
    if not sample_sets:
        return [[]]
    base = [samples[0] for samples in sample_sets]
    cases = [list(base)]
    for index, samples in enumerate(sample_sets):
        for sample in samples[1:4]:
            variant = list(base)
            variant[index] = sample
            cases.append(variant)
            if len(cases) >= 8:
                return cases
    return cases


def execute(module_path: Path, cases: list[dict]) -> list[dict]:
    with tempfile.TemporaryDirectory() as directory:
        payload_path = Path(directory) / "cases.json"
        payload_path.write_text(json.dumps({"cases": cases}), encoding="utf-8")
        completed = subprocess.run(
            ["node", "--experimental-strip-types", str(PROBE), str(module_path.resolve()), str(payload_path)],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
            env=child_env(),
        )
    if completed.returncode != 0 or not completed.stdout.strip():
        return []
    try:
        parsed = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []


def to_ts(value) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        escaped = value.replace("\\", "\\\\").replace("'", "\\'")
        return f"'{escaped}'"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        return "[" + ", ".join(to_ts(item) for item in value) + "]"
    if isinstance(value, dict):
        fields = ", ".join(f"{key}: {to_ts(item)}" for key, item in value.items())
        return "{ " + fields + " }"
    return "null"
