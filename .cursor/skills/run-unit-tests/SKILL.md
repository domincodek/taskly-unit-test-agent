---
name: run-unit-tests
description: Runs the pytest and Vitest files selected for a change and records exit codes and output. Use after tests are authored or when existing tests only need verification.
---

# Run unit tests

Run only the selected test files.

- Backend: `python -m pytest <files> -q --tb=short` from the repository root.
- Frontend: `npm test -- <files>` from `frontend`.

Pass a scrubbed environment to the test process. Do not pass GitHub tokens, passwords, or API keys. Treat a non-zero exit code as a failed verification.
