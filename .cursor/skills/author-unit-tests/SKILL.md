---
name: author-unit-tests
description: Creates or updates Vitest and pytest unit tests for changed React and FastAPI code. Use when assessment says tests should be authored.
---

# Author unit tests

Write tests that match the repository conventions:

- Backend tests live in `backend/tests` and import the `app` package.
- Frontend tests sit beside the source file and use Vitest with Testing Library.
- Pure functions are characterized by executing them on small typed samples and asserting the observed result.
- FastAPI app wiring, health, configuration, lifespan, database helpers, fetch wrappers, React Query hooks, and simple boolean-copy components use the matching pattern.

Never create or modify application source, workflow files, or environment files. If a human-authored test already references a function, append only a missing behavior test. If no strategy can produce a check that is likely to pass, leave the file unchanged and say so.
