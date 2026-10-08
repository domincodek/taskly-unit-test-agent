---
name: analyze-changes
description: Reads a pull request diff or repository gap list and returns changed frontend and backend files. Use when deciding which application code a unit-test agent should inspect.
---

# Analyze changes

Collect changed paths for the selected scope.

- `pull-request` compares the base and head revisions with git.
- `working-tree` includes tracked edits and untracked files.
- `gaps` lists application modules that participate in unit-test coverage.

Keep deleted paths in the result, but do not treat documentation, workflow files, the design system, schemas, models, or existing tests as authoring targets.
