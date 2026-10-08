from ...domain.models import AgentState


def render_comment(state: AgentState) -> str:
    lines = [
        "<!-- taskly-unit-test-agent -->",
        "## Unit test agent",
        "",
        state.assessment.summary if state.assessment else "The agent did not finish the assessment.",
        "",
        "### Skills",
    ]
    for event in state.log:
        lines.append(f"- `{event.skill}`: {event.summary}")
    if state.assessment and state.assessment.targets:
        lines.extend(["", "### Targets"])
        for target in state.assessment.targets:
            lines.append(f"- `{target.source_path}`: {target.reason}")
    if state.authored:
        lines.extend(["", "### Test files"])
        for item in state.authored:
            lines.append(f"- `{item.path}`: {item.action}. {item.summary}")
    if state.verification:
        status = "passed" if state.verification.passed else "failed"
        lines.extend(["", f"### Verification: {status}"])
        for command in state.verification.commands:
            lines.extend(
                [
                    "",
                    f"`{command.command}` exited {command.code}.",
                    "",
                    "<details>",
                    "<summary>Command output</summary>",
                    "",
                    "```text",
                    command.output[-3500:],
                    "```",
                    "",
                    "</details>",
                ]
            )
        if not state.verification.commands:
            lines.append("")
            lines.append("There were no test commands to run.")
    if state.assessment and state.assessment.skipped:
        lines.extend(["", "### Left unchanged"])
        for path, reason in state.assessment.skipped[:30]:
            lines.append(f"- `{path}`: {reason}")
    lines.extend(
        [
            "",
            "The agent only writes files under `backend/tests` and `frontend/src/**/*.test.ts(x)`.",
        ]
    )
    return "\n".join(lines) + "\n"
