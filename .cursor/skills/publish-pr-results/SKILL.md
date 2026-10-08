---
name: publish-pr-results
description: Writes the agent report and upserts one GitHub pull request comment with the decision, skills used, test files, and command output. Use as the final step of the unit-test agent.
---

# Publish pull request results

Save `agent/reports/result.json` and `agent/reports/comment.md`.

When `GITHUB_REPOSITORY`, `PR_NUMBER`, and `GITHUB_TOKEN` are present, create or update the pull request comment that starts with `<!-- taskly-unit-test-agent -->`. Update that comment on later runs instead of adding another one.

The comment must include the decision, every skill that ran, the test files touched, and the verification output.
