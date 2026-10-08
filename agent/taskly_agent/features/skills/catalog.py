from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SkillDoc:
    name: str
    description: str
    path: str


def load_skill_docs(root: Path) -> dict[str, SkillDoc]:
    directory = root / ".cursor" / "skills"
    if not directory.is_dir():
        raise FileNotFoundError(f"Missing skill catalog: {directory}")
    docs: dict[str, SkillDoc] = {}
    for skill_file in sorted(directory.glob("*/SKILL.md")):
        text = skill_file.read_text(encoding="utf-8")
        if not text.startswith("---"):
            raise ValueError(f"Skill is missing frontmatter: {skill_file}")
        _, raw, _body = text.split("---", 2)
        fields: dict[str, str] = {}
        for line in raw.strip().splitlines():
            key, value = line.split(":", 1)
            fields[key.strip()] = value.strip().strip('"').strip("'")
        name = fields["name"]
        docs[name] = SkillDoc(
            name=name,
            description=fields["description"],
            path=skill_file.relative_to(root).as_posix(),
        )
    return docs
