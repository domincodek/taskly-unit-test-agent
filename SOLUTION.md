# Solution

## Decisions

The test agent is a Python program in `agent/taskly_agent`, not a free-form model call. A pull request needs a repeatable result: the same diff should produce the same tests, and those tests must actually run. An unbounded model can write plausible tests that do not pass, and it would require an API key in CI. The agent instead keeps a short state and chooses the next skill from that state.

The skills are the six directories in `.cursor/skills`. Each `SKILL.md` is the contract (name, when it applies, and the rule it must follow). The executable step lives in the matching Python feature module. On startup the agent loads the catalog and stops if a skill file has no implementation, or an implementation has no skill file. That keeps the written skills and the code that runs them the same set.

Authoring is limited to shapes the runner can check:

- pure Python and TypeScript functions are called in a short-lived process on a few values derived from their type annotations, and the test asserts the value that came back
- FastAPI application wiring, health, database URL configuration, lifespan, session helpers, and the repository dependency use structural tests
- the frontend covers the fetch wrapper, React Query hooks, the notice timer was already a hook under test, and components whose props are booleans or callbacks and whose copy is a boolean ternary

The author may create or update files only under `backend/tests/**/*.py` and `frontend/src/**/*.test.ts(x)`. A path outside that sandbox raises before anything is written. Files the agent created are marked and can be regenerated. A test file written by a person is only appended to, and only for a case that is not already named there.

Verification runs `pytest` and `vitest` on the test files touched in that run. The child process receives a copy of the environment with tokens, passwords, and keys removed. If the command fails, `repair-unit-tests` schedules one more run. It does not edit application code to force a pass. The outcome is written to `agent/reports/result.json` and, when GitHub credentials are present, upserted into a single pull request comment that starts with `<!-- taskly-unit-test-agent -->`.

The workflow file is `.github/workflows/unit-test-agent.yml`. It runs only for pull requests whose head branch is in this repository. The agent code and skill files are taken from the base revision, and the tests are written into the pull request checkout. The test run itself does not receive `GITHUB_TOKEN`. A later step publishes the comment and, only after a passing run, commits the test files back to the head branch.

## How to run it

Prerequisites:

- Python 3.11 or newer and Node.js 22 or newer
- backend dependencies from `backend/requirements.txt`
- `npm ci` in `frontend`
- for the GitHub comment and the commit back to the branch: Actions enabled on the repository, and the workflow present on the default branch
- the pull request must come from the same repository; forks are ignored

Local agent check:

```sh
cd agent
python -m pytest
```

Local run from the repository root, after the two installs above:

```sh
python -m taskly_agent run --scope pull-request --base <base-sha> --head <head-sha> --root .
python -m taskly_agent publish --root .
```

`PYTHONPATH` must include the `agent` directory. `publish` posts the saved comment when `GITHUB_REPOSITORY`, `PR_NUMBER`, and `GITHUB_TOKEN` are set. Without them it leaves `agent/reports/comment.md` in place.

`gaps` scans the application for units that are not referenced by a test. `working-tree` uses the current git diff plus untracked files. The workflow uses `pull-request`.

## Where the agent and skills live

| Skill | Contract | Implementation |
| --- | --- | --- |
| `analyze-changes` | `.cursor/skills/analyze-changes/SKILL.md` | `agent/taskly_agent/features/changes/collect.py` |
| `assess-test-need` | `.cursor/skills/assess-test-need/SKILL.md` | `agent/taskly_agent/features/assessment/assess.py` |
| `author-unit-tests` | `.cursor/skills/author-unit-tests/SKILL.md` | `agent/taskly_agent/features/authoring/` |
| `run-unit-tests` | `.cursor/skills/run-unit-tests/SKILL.md` | `agent/taskly_agent/features/verification/skill.py` |
| `repair-unit-tests` | `.cursor/skills/repair-unit-tests/SKILL.md` | `agent/taskly_agent/orchestration/loop.py` |
| `publish-pr-results` | `.cursor/skills/publish-pr-results/SKILL.md` | `agent/taskly_agent/features/publishing/` |

`agent/taskly_agent/orchestration/policy.py` picks the next skill. `orchestration/loop.py` applies it and records the summary. The workflow calls `python -m taskly_agent run`.

## Example run

The progress summary is a small feature on both sides: `backend/app/features/todos/progress.py`, `frontend/src/features/todos/utils/progress.ts`, and `TaskProgress`, which the task page renders. A `gaps` run on that tree made these decisions:

1. `analyze-changes`: 39 application paths were in scope.
2. `assess-test-need`: 16 units needed tests. Thirteen of those were agent-owned files being refreshed. The three new units had no tests yet. The decision was to author.
3. `author-unit-tests`: three files were written. The refreshed files were already current, so they were left unchanged.
   - `backend/tests/features/todos/test_progress.py`
   - `frontend/src/features/todos/utils/progress.test.ts`
   - `frontend/src/features/todos/components/TaskProgress.test.tsx`
4. `run-unit-tests`: pytest and vitest both passed. `repair-unit-tests` was not used.
5. `publish-pr-results`: the report was saved locally because this run had no pull request token.

The generated backend checks include `remaining_count([]) == 0`, `remaining_count([False, True]) == 1`, and `completion_percent([False, True]) == 50`. The frontend file asserts the same behavior for `remainingCount` and `completionPercent`. The component test renders both copies: "Some tasks are still open." and "All tasks are complete."

An earlier run did use `repair-unit-tests`. The factory assertion looked for `/api/health` on the top-level route list, and the empty-state test mocked the wrong module id, so the design-system theme was missing. The retry failed the same way, the agent published the failure, and it did not treat the application source as something it could edit. The generators were corrected and the next run passed.

After that work the suites were:

- backend: 53 passed, 99% line coverage of `app` (`main.py` is the uncovered module; the project coverage config already omits it)
- frontend: 55 passed, 82.91% lines / 82.48% statements inside the Vitest coverage include
- agent: 8 passed

Health, configuration, lifespan, the app factory, the database helpers, the repository dependency, the repository, the todo router, the HTTP client, the todo hooks, and the progress helpers are covered by these runs.

## Assumptions

- Python 3.11 syntax and Node's type-stripping flag are available in CI.
- Same-repository pull requests are the ones that should receive commits. A fork must not run this job with write credentials.
- The existing test layout is the convention: `backend/tests/test_<module>.py` and a sibling `*.test.ts` or `*.test.tsx`.
- Design-system stories, type-only modules, schemas, models, and `main.py` stay outside the authoring boundary, matching the coverage excludes already in the repo.
- A pure function's type annotations are enough to build a few safe inputs. If they are not, the agent skips that function instead of guessing.

## Limitations

- The author does not invent tests for arbitrary UI state, SQLAlchemy query behavior, or route handlers that already have a human test file but do not name the Python function. Route and repository gaps in the original app were covered with ordinary tests in the existing files; the agent fills modules it can characterize safely.
- Characterization imports the changed module. The subprocess is time-limited and does not receive secrets, but it is not a hardened sandbox.
- Agent-owned tests are regenerated from samples, so a later run can rewrite their formatting. Human tests are not rewritten.
- The workflow does not run for fork pull requests, and a pull request that deletes a skill file on the base branch is not what executes: execution uses the base revision.
- `TodosPage` and parts of the editor, list, and delete dialog still have branch gaps. The agent left them alone because a test file already references those components and their props do not match the boolean-copy pattern.

## Production changes

- Run characterization in a sandbox with no network and a read-only source tree.
- Pin the GitHub Actions by commit SHA and restrict the workflow token further.
- Add a model-backed author only behind the same path guard, and only accept its patch after pytest and vitest pass.
- Fail the check when a changed public function has no strategy and no existing test, instead of only commenting.
- Comment on the changed lines, and skip draft or documentation-only pull requests before the agent starts.
- Keep a coverage floor per feature package so a new feature cannot merge while its own module is untested.
