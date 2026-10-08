import os
from pathlib import Path

from ..domain.models import AgentState, RunContext, SkillEvent
from ..features.assessment.assess import assess
from ..features.authoring.skill import execute as author
from ..features.changes.collect import collect_changes
from ..features.publishing.skill import execute as publish
from ..features.skills.catalog import load_skill_docs
from ..features.verification.skill import execute as verify
from .policy import next_skill


def run_agent(context: RunContext) -> AgentState:
    catalog_root = Path(os.environ.get("TASKLY_SKILL_ROOT", context.root))
    docs = load_skill_docs(catalog_root)
    available = {
        "analyze-changes",
        "assess-test-need",
        "author-unit-tests",
        "run-unit-tests",
        "repair-unit-tests",
        "publish-pr-results",
    }
    if set(docs) != available:
        missing = sorted(available.symmetric_difference(docs))
        raise RuntimeError(f"Skill catalog does not match the agent: {', '.join(missing)}")
    state = AgentState()
    for _step in range(8):
        skill = next_skill(state)
        if skill is None:
            break
        summary = apply_skill(skill, state, context)
        state.log.append(SkillEvent(skill, summary))
    else:
        if next_skill(state) is not None:
            raise RuntimeError("The agent did not finish within the skill step limit.")
    return state


def apply_skill(skill: str, state: AgentState, context: RunContext) -> str:
    root = Path(context.root)
    if skill == "analyze-changes":
        state.changes = collect_changes(root, context.scope, context.base, context.head)
        return f"Collected {len(state.changes.files)} changed path(s) in scope {context.scope}."
    if skill == "assess-test-need":
        state.assessment = assess(root, state.changes)
        return state.assessment.summary
    if skill == "author-unit-tests":
        summary, authored = author(state, context)
        state.authored = authored
        return summary
    if skill == "run-unit-tests":
        summary, verification = verify(state, context)
        state.verification = verification
        return summary
    if skill == "repair-unit-tests":
        state.repairs += 1
        state.verification = None
        return "Scheduled one more test run after the failure."
    if skill == "publish-pr-results":
        summary, _mode = publish(state, context)
        state.published = True
        return summary
    raise RuntimeError(f"Unknown skill: {skill}")
