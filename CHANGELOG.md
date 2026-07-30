# Changelog

## Unreleased

### Added - Phase 1.1: Project Foundation

Backend skeleton (FastAPI) structured per Clean Architecture layering: api, config, core, database, dependencies, middleware, exceptions, repositories, services, utils, workers

Frontend skeleton (Next.js, TypeScript, Tailwind, shadcn/ui) structured per the documented frontend folder layout

Docker and Docker Compose setup for frontend, backend, worker, PostgreSQL, and Redis, with healthchecks

uv adopted as the official backend dependency manager (ADR-021)

Structured JSON logging via structlog, shared between FastAPI and future Celery workers, with correlation ID propagation and sensitive-data redaction

Liveness (`/health`) and readiness (`/health/ready`) endpoints

Alembic migration scaffolding wired to centralized configuration

CI foundation via GitHub Actions (ruff, mypy, pytest, eslint, typecheck, build)

Development tooling: ruff, mypy, black, pytest (backend); eslint, prettier, TypeScript strict mode (frontend)

### Status

Phase 1 (Project Foundation) is complete. See `docs/30_DEVELOPMENT_ROADMAP.md`.

---

## Version 1.0.0

### Added

Complete software architecture

36 engineering documents

AI architecture

Frontend guidelines

Backend guidelines

Database design

API specification

Development roadmap

---

Future releases will follow Semantic Versioning.