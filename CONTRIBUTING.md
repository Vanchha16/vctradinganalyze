# Contributing

Thank you for contributing.

---

## Workflow

Feature Branch

↓

Development

↓

Pull Request

↓

Code Review

↓

Testing

↓

Merge

---

## Standards

Follow:

31_CODING_STANDARDS.md

---

## Pull Requests

- Small
- Focused
- Tested
- Documented

---

## CI

`.github/workflows/ci.yml` runs three required checks on every push/PR:
`backend` (ruff, mypy, Alembic against Postgres, pytest with a 90%
coverage floor), `frontend` (lint, typecheck, build), and `e2e`
(Playwright against a production frontend build and a `--e2e-db`-backed
backend, Chromium only). All three block merge - `e2e` included, per
ADR-135 (`docs/36_DECISION_RECORDS.md`).

To reproduce the `e2e` job locally before pushing, see README.md
"Running the E2E suite" - the CI-reproduction variant near the bottom of
that section builds and starts the frontend the same way CI does
(`next build` + `next start`), rather than `next dev`.

---

## Commit Format

feat:

fix:

refactor:

docs:

test:

ci:

build:

style: