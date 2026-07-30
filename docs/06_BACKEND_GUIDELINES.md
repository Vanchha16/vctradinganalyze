# Backend Engineering Guidelines

Version: 1.0

---

# 1. Objective

Build an enterprise-grade backend that is:

- Scalable
- Secure
- Modular
- Testable
- Maintainable
- Production Ready

The backend must follow:

- Clean Architecture
- SOLID Principles
- Repository Pattern
- Service Layer Pattern
- Dependency Injection

---

# 2. Technology Stack

Framework

- FastAPI

Language

- Python 3.13+

Database

- PostgreSQL

ORM

- SQLAlchemy 2.x

Migration

- Alembic

Validation

- Pydantic v2

Authentication

- JWT
- OAuth2
- Google OAuth

Background Jobs

- Celery

Message Broker

- Redis

API Documentation

- OpenAPI
- Swagger UI

Dependency Management

- uv

Containerization

- Docker

---

# 3. Folder Structure

backend/

app/

api/

core/

config/

dependencies/

middleware/

models/

schemas/

repositories/

services/

ai/

indicators/

smc/

signals/

news/

economic/

workers/

utils/

exceptions/

database/

tests/

alembic/

scripts/

---

# 4. Clean Architecture

Presentation Layer

↓

API Layer

↓

Service Layer

↓

Repository Layer

↓

Database

Rules

API routes never access the database.

Repositories never contain business logic.

Services never contain SQL queries.

Business rules stay inside Services.

---

# 5. Dependency Injection

Every Service must receive its dependencies through constructor injection.

Never instantiate repositories inside services.

Correct

SignalService(repository)

Incorrect

repository = SignalRepository()

---

# 6. Repository Pattern

Repositories handle:

CRUD

Queries

Filtering

Pagination

Transactions

Repositories never perform calculations.

---

# 7. Service Layer

Services handle:

Business Rules

AI Workflow

Validation

Signal Generation

Permission Checks

Notifications

No SQL inside Services.

---

# 8. API Layer

Responsibilities

Request Validation

Authentication

Authorization

Response Formatting

Exception Handling

No business logic.

---

# 9. Pydantic

Every endpoint uses:

Request Schema

Response Schema

Never return ORM models directly.

---

# 10. Database

Use SQLAlchemy ORM.

Avoid raw SQL unless necessary.

Use relationships.

Use UUID primary keys.

Use UTC timestamps.

Soft delete when appropriate.

---

# 11. Transactions

Use transactions when modifying multiple related tables.

Rollback automatically on failure.

---

# 12. Error Handling

Create custom exceptions.

Example

BusinessException

AuthenticationException

PermissionDeniedException

ResourceNotFoundException

ValidationException

Never expose internal errors to clients.

---

# 13. Logging

Log

Requests

Errors

Warnings

Background Jobs

AI Analysis

Authentication

Use structured JSON logs.

Never log passwords or tokens.

---

# 14. Configuration

Use environment variables.

Never hardcode:

Passwords

API Keys

Secrets

URLs

Environment Variables

DATABASE_URL

REDIS_URL

OPENAI_API_KEY

JWT_SECRET

SMTP_HOST

SMTP_PORT

TELEGRAM_BOT_TOKEN

NEWS_API_KEY

ECONOMIC_API_KEY

---

# 15. Security

HTTPS Only

JWT Authentication

Argon2 Password Hashing

Rate Limiting

CORS

Input Validation

Parameterized Queries

XSS Prevention

CSRF Protection (where applicable)

Security Headers

---

# 16. Background Workers

Celery Tasks

Generate Signals

Analyze News

Calculate Indicators

Refresh Economic Events

Send Telegram Messages

Daily Reports

Cleanup Jobs

Workers must be idempotent.

---

# 17. Redis

Store

Cache

Sessions

Rate Limits

Task Queue

Temporary AI Results

Never store permanent business data.

---

# 18. AI Module

AI modules must never call the database directly.

Input

Market Data

Indicators

SMC

News

Economic Events

Output

Recommendation

Confidence

Reasoning

Risk

Entry

Stop Loss

Take Profit

---

# 19. API Standards

RESTful Naming

Good

GET /signals

GET /signals/{id}

POST /signals

Bad

GET /getSignals

POST /createSignal

---

# 20. Pagination

Always paginate list endpoints.

Example

?page=1

&limit=20

Maximum limit

100

---

# 21. Testing

pytest

Coverage Goal

>90%

Test Types

Unit

Integration

API

Background Tasks

AI Services (mocked)

---

# 22. Documentation

Every public function must include docstrings.

Every module must include documentation.

Complex algorithms require inline comments explaining the reasoning.

---

# 23. Coding Style

PEP8

Type Hints

Meaningful Names

No Magic Numbers

Small Functions

Single Responsibility

Avoid Deep Nesting

---

# 24. Performance

API <300ms

Async where appropriate

Database Indexes

Connection Pooling

Caching

Avoid N+1 Queries

Batch Operations

---

# 25. Monitoring

Health Endpoint

Metrics Endpoint

Prometheus Ready

Structured Logs

Error Tracking

Background Task Monitoring

---

# 26. Future Scalability

Microservices Ready

Horizontal Scaling

Independent AI Workers

Message Queue Architecture

Read Replicas

Object Storage

Multi-region Deployment

---

# 27. Definition of Done

A backend feature is complete only if:

✔ Business logic implemented

✔ API documented

✔ Tests written

✔ Type hints added

✔ Logging included

✔ Validation added

✔ Error handling added

✔ Docker compatible

✔ Lint passes

✔ Documentation updated