from dataclasses import dataclass, field


@dataclass(frozen=True)
class ChangedFile:
    path: str
    status: str


@dataclass(frozen=True)
class ChangeSet:
    files: tuple[ChangedFile, ...]
    base: str
    head: str
    scope: str


@dataclass(frozen=True)
class UnitTarget:
    source_path: str
    test_path: str
    reason: str


@dataclass(frozen=True)
class Assessment:
    action: str
    summary: str
    targets: tuple[UnitTarget, ...]
    skipped: tuple[tuple[str, str], ...]
    verify_paths: tuple[str, ...]


@dataclass(frozen=True)
class AuthoredFile:
    path: str
    action: str
    summary: str


@dataclass(frozen=True)
class CommandResult:
    command: str
    code: int
    output: str


@dataclass(frozen=True)
class Verification:
    passed: bool
    commands: tuple[CommandResult, ...]


@dataclass(frozen=True)
class SkillEvent:
    skill: str
    summary: str


@dataclass
class AgentState:
    changes: ChangeSet | None = None
    assessment: Assessment | None = None
    authored: tuple[AuthoredFile, ...] | None = None
    verification: Verification | None = None
    repairs: int = 0
    published: bool = False
    log: list[SkillEvent] = field(default_factory=list)


@dataclass(frozen=True)
class RunContext:
    root: str
    scope: str
    base: str | None
    head: str | None
    repository: str | None
    pr_number: str | None
    token: str | None
