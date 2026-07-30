# System Architecture

Version: 1.0

---

# 1. Architecture Style

The system follows **Clean Architecture** with Domain-Driven Design (DDD) principles.

Goals:

- High scalability
- Loose coupling
- Easy testing
- Easy maintenance
- Independent modules

The application is divided into:

- Frontend
- Backend API
- AI Engine
- Background Workers
- Database
- Cache
- External Services

---

# 2. High-Level Architecture

                    ┌────────────────────────┐
                    │      Web Browser       │
                    └───────────┬────────────┘
                                │
                        HTTPS / WebSocket
                                │
                    ┌───────────▼────────────┐
                    │       Next.js App      │
                    └───────────┬────────────┘
                                │ REST API
                    ┌───────────▼────────────┐
                    │      FastAPI API       │
                    └───────────┬────────────┘
              ┌─────────────────┼─────────────────┐
              │                 │                 │
       PostgreSQL           Redis Cache       Celery Queue
              │                 │                 │
              └─────────────────┼─────────────────┘
                                │
                     AI Analysis Engine
                                │
         ┌──────────────┬──────────────┬──────────────┐
         │              │              │
 Technical Engine   News Engine    Economic Engine
         │              │              │
         └──────────────┴──────────────┘
                     Signal Engine
                                │
                     Telegram / Dashboard

---

# 3. Project Structure

project/

├── frontend/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── repositories/
│   │   ├── workers/
│   │   ├── ai/
│   │   ├── indicators/
│   │   ├── smc/
│   │   ├── news/
│   │   ├── economic/
│   │   ├── signals/
│   │   └── utils/
│   │
│   ├── tests/
│   └── alembic/
│
├── docs/
├── docker/
├── scripts/

---

# 4. Frontend Architecture

Framework:

- Next.js App Router
- React
- TypeScript

Structure

app/

components/

hooks/

services/

store/

types/

utils/

styles/

Features

Authentication

Dashboard

Signals

Charts

Economic Calendar

News

Profile

Admin

---

# 5. Backend Architecture

Layers

Presentation Layer

↓

API Layer

↓

Service Layer

↓

Repository Layer

↓

Database

No API route may access the database directly.

All business logic belongs in the Service Layer.

---

# 6. Repository Pattern

API

↓

Service

↓

Repository

↓

Database

Repositories are responsible only for data access.

Services contain business logic.

---

# 7. AI Pipeline

Market Data

↓

Indicators

↓

Smart Money Concepts

↓

Economic Events

↓

News Sentiment

↓

Risk Engine

↓

AI Reasoning

↓

Signal Generation

↓

Database

↓

Dashboard

↓

Telegram

---

# 8. Signal Lifecycle

Receive live market data

↓

Calculate indicators

↓

Detect market structure

↓

Analyze news

↓

Analyze economic calendar

↓

Calculate confidence

↓

Generate recommendation

↓

Save signal

↓

Notify users

---

# 9. External Services

TradingView

OpenAI

News Provider

Economic Calendar Provider

Telegram Bot API

Email Provider

---

# 10. Authentication Flow

User

↓

Login

↓

JWT Access Token

↓

Refresh Token

↓

Protected API

↓

Authorized Response

---

# 11. Background Jobs

Celery handles:

News collection

Economic updates

Signal generation

AI analysis

Telegram messages

Cleanup tasks

---

# 12. Redis

Redis stores:

Sessions

Cache

Background queues

Rate limits

Temporary AI results

---

# 13. WebSocket

Used for:

Live prices

Signal updates

Dashboard refresh

Notifications

---

# 14. Logging

Every request is logged.

Every AI response is logged.

Every error is logged.

Audit logs are stored for admin review.

---

# 15. Security

HTTPS only

JWT Authentication

Role-Based Access Control (RBAC)

Password hashing (Argon2)

Environment variables

Rate limiting

Input validation

SQL injection prevention

XSS prevention

CORS configuration

---

# 16. Scalability

The platform should support:

10,000+ concurrent users

Horizontal scaling

Stateless API servers

Load balancing

Independent AI workers

---

# 17. Coding Principles

- SOLID
- DRY
- KISS
- Clean Code
- Dependency Injection
- Repository Pattern
- Service Layer Pattern

No business logic inside API routes.

No SQL inside controllers.

No duplicated logic.