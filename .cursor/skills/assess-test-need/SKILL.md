---
name: assess-test-need
description: Decides whether changed frontend or backend code needs new or updated unit tests. Use after the change list is known and before any test file is written.
---

# Assess test need

Choose one action:

- `author` when a public function, component, or uncovered branch has no referencing test.
- `verify` when the change already has tests or only test files changed.
- `skip` when nothing in the change belongs to the unit-test boundary.

Do not request tests for generated files, Storybook stories, type-only modules, or the design system. Leave deleted source files and their tests untouched.
