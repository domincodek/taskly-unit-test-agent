import json
import os
from pathlib import Path

from ...domain.models import AgentState, RunContext
from .comment import render_comment
from .github import upsert_comment


def execute(state: AgentState, context: RunContext) -> tuple[str, str]:
    root = Path(context.root)
    comment = render_comment(state)
    report = root / "agent" / "reports"
    report.mkdir(parents=True, exist_ok=True)
    files = []
    if state.authored:
        files = [
            {"path": item.path, "action": item.action, "summary": item.summary}
            for item in state.authored
        ]
    commands = []
    if state.verification:
        commands = [
            {"command": item.command, "code": item.code, "output": item.output}
            for item in state.verification.commands
        ]
    passed = state.verification.passed if state.verification else True
    payload = {
        "decision": state.assessment.action if state.assessment else "unknown",
        "summary": state.assessment.summary if state.assessment else "",
        "passed": passed,
        "repairs": state.repairs,
        "skills": [{"name": event.skill, "summary": event.summary} for event in state.log],
        "files": files,
        "commands": commands,
        "comment": comment,
    }
    (report / "result.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8", newline="\n")
    (report / "comment.md").write_text(comment, encoding="utf-8", newline="\n")
    if context.token and context.repository and context.pr_number:
        mode = upsert_comment(context.repository, context.pr_number, context.token, comment)
        return f"Published the pull request comment ({mode}).", "published"
    return "Saved the report locally. No pull request credentials were configured.", "local"


def publish_saved(root: Path) -> str:
    report = root / "agent" / "reports" / "result.json"
    if not report.exists():
        return "No agent report was produced."
    payload = json.loads(report.read_text(encoding="utf-8"))
    repository = os.environ.get("GITHUB_REPOSITORY")
    number = os.environ.get("PR_NUMBER")
    token = os.environ.get("GITHUB_TOKEN")
    if not repository or not number or not token:
        return "Saved report only. GitHub publish needs GITHUB_REPOSITORY, PR_NUMBER, and GITHUB_TOKEN."
    mode = upsert_comment(repository, number, token, payload["comment"])
    return f"Published the pull request comment ({mode})."
