from ..domain.models import AgentState

MAX_REPAIRS = 1


def next_skill(state: AgentState) -> str | None:
    if state.published:
        return None
    if state.changes is None:
        return "analyze-changes"
    if state.assessment is None:
        return "assess-test-need"
    if state.assessment.action == "skip":
        return "publish-pr-results"
    if state.assessment.action == "author" and state.authored is None:
        return "author-unit-tests"
    if state.verification is None:
        return "run-unit-tests"
    if (
        not state.verification.passed
        and state.verification.commands
        and state.repairs < MAX_REPAIRS
    ):
        return "repair-unit-tests"
    return "publish-pr-results"
