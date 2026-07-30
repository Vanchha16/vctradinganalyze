# Coding Standards

Version: 1.0

---

# 1. Objective

Ensure consistent, maintainable, and scalable code across the entire project.

---

# 2. General Principles

- SOLID
- DRY
- KISS
- Clean Architecture
- Domain Driven Design (DDD)
- Separation of Concerns

---

# 3. Naming Convention

Python

snake_case

Classes

PascalCase

Constants

UPPER_CASE

React Components

PascalCase

Hooks

useSomething

Files

kebab-case

API Routes

RESTful naming

---

# 4. Folder Rules

One responsibility per module.

Maximum nesting:

4 levels

No business logic inside controllers.

---

# 5. Type Safety

Backend

Strict typing

Frontend

TypeScript Strict Mode

No any unless justified.

---

# 6. Error Handling

Centralized exception handlers.

Never expose internal stack traces.

Return standardized error responses.

---

# 7. Logging

Structured JSON logs.

Correlation ID required.

No sensitive data.

---

# 8. Documentation

Every public function must include:

Purpose

Arguments

Returns

Exceptions

---

# 9. Git

Feature branches

Conventional Commits

Small pull requests

Mandatory code review

---

# 10. Code Quality

Black

Ruff

ESLint

Prettier

MyPy

Coverage ≥95%