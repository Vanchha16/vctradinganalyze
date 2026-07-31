# Architecture Decision Records (ADR)

Version: 1.0

---

# Objective

This document records significant architectural and technical decisions made throughout the project.

Each decision must include:

- Context
- Decision
- Reasoning
- Trade-offs
- Consequences
- Status

Architecture decisions should never rely solely on memory.

---

# ADR Template

## ADR-XXX

Title

Date

Status

Accepted

Context

Describe the problem.

Decision

Describe the chosen solution.

Reason

Explain why.

Alternatives Considered

Option A

Option B

Option C

Trade-offs

Pros

Cons

Consequences

Positive

Negative

Future Review

When should this decision be revisited?

---

# ADR-001

Title

Use FastAPI as Backend Framework

Status

Accepted

Context

The backend requires:

- High performance
- Async support
- OpenAPI generation
- Excellent typing
- Modern architecture

Decision

Use FastAPI.

Reason

Excellent async support.

Automatic API documentation.

Strong typing.

Large ecosystem.

Trade-offs

Pros

Fast

Clean

Scalable

Cons

Smaller ecosystem than Django.

Future Review

Review every major FastAPI release.

---

# ADR-002

Title

Use Next.js for Frontend

Status

Accepted

Reason

SSR

Excellent React ecosystem

TypeScript

SEO support

App Router

Future Review

Evaluate major Next.js releases.

---

# ADR-003

Title

Use PostgreSQL

Status

Accepted

Reason

Reliable

Powerful indexing

JSON support

Scalable

Excellent tooling

---

# ADR-004

Title

Use Redis

Status

Accepted

Reason

Caching

Queues

Rate Limiting

WebSocket Support

Fast lookups

---

# ADR-005

Title

Separate AI from Business Logic

Status

Accepted

Decision

AI performs reasoning only.

Business rules remain deterministic.

Reason

Prevent hallucinations.

Improve testing.

Increase explainability.

Trade-offs

Pros

Reliable

Predictable

Auditable

Cons

More engineering effort.

---

# ADR-006

Title

Use Deterministic Technical Engines

Status

Accepted

Decision

Indicators are calculated in code.

Never by AI.

Reason

Accuracy

Repeatability

Testing

Auditability

---

# ADR-007

Title

AI Never Invents Market Data

Status

Accepted

Decision

AI receives structured evidence only.

Reason

Prevent hallucinations.

Increase trust.

Improve consistency.

---

# ADR-008

Title

Evidence-Based Architecture

Status

Accepted

Decision

Every engine publishes evidence.

Signal Engine consumes evidence.

Reason

Loose coupling.

Independent testing.

Better explainability.

---

# ADR-009

Title

Modular Engine Design

Status

Accepted

Decision

Each domain has its own engine.

Examples

Technical

SMC

Risk

News

Economic

Confidence

Reason

Independent development.

Scalable architecture.

Easy maintenance.

---

# ADR-010

Title

Signal Generation Requires Confluence

Status

Accepted

Decision

Signals are never generated from a single indicator.

Reason

Reduce false positives.

Increase signal quality.

Encourage institutional-style analysis.

---

# ADR-011

Title

WAIT is a Valid Recommendation

Status

Accepted

Decision

The platform may recommend WAIT.

Reason

No trade is often better than a poor trade.

Trade-offs

Pros

Protects users.

Builds trust.

Cons

Fewer signals.

---

# ADR-012

Title

Market Regime Before Strategy Selection

Status

Accepted

Decision

Determine market regime before selecting a strategy.

Reason

Different strategies perform better under different conditions.

---

# ADR-013

Title

Confidence Must Be Explainable

Status

Accepted

Decision

Every confidence score must include strengths and penalties.

Reason

Transparency.

User trust.

Debugging.

---

# ADR-014

Title

Risk Engine Can Reject Signals

Status

Accepted

Decision

The Risk Engine has veto authority.

Reason

Protect users during high-risk conditions.

Examples

Major economic events

Extreme volatility

Low liquidity

---

# ADR-015

Title

Admin Replay Capability

Status

Accepted

Decision

Every AI decision must be replayable.

Reason

Debugging.

Compliance.

Continuous improvement.

---

# ADR-016

Title

API-First Architecture

Status

Accepted

Decision

Every feature is exposed through the API before UI implementation.

Reason

Supports web, mobile, Telegram, and future integrations.

---

# ADR-017

Title

Configuration Over Hardcoding

Status

Accepted

Decision

Strategies, providers, thresholds, and feature behavior should be configurable whenever practical.

Reason

Simplifies maintenance.

Supports future expansion.

Reduces code changes.

---

# ADR-018

Title

Version Everything

Status

Accepted

Decision

Version prompts, AI models, APIs, database schema, engines, and configuration.

Reason

Rollback capability.

Reproducibility.

Historical analysis.

---

# ADR-019

Title

Observability by Default

Status

Accepted

Decision

Every critical service must expose metrics, logs, and health checks.

Reason

Simplifies troubleshooting.

Improves reliability.

Supports proactive monitoring.

---

# ADR-020

Title

Security by Design

Status

Accepted

Decision

Security requirements are integrated into architecture from the beginning rather than added later.

Reason

Reduce vulnerabilities.

Simplify compliance.

Protect user trust.

---

# Future ADRs

Every major architectural change requires a new ADR.

Existing ADRs should never be overwritten.

If a decision changes:

Old ADR

↓

Superseded

↓

New ADR

This preserves historical context.

---

# ADR Lifecycle

Proposed

↓

Under Review

↓

Accepted

↓

Implemented

↓

Deprecated (Optional)

↓

Superseded (Optional)

---

# ADR-021

Title

Use uv as Python Dependency Manager

Status

Accepted

Context

The backend needs a fast, reproducible, single-source-of-truth dependency management workflow for Python packages and virtual environments.

Decision

Use uv for all backend dependency management (installing, locking, running scripts). `pyproject.toml` is the single source of dependency declarations; `uv.lock` is committed for reproducible installs. `requirements.txt` is no longer used.

Reason

Significantly faster installs and locking than pip.

Single tool for virtualenv creation, dependency resolution, and locking.

Reproducible builds via a committed lockfile.

Growing ecosystem adoption.

Trade-offs

Pros

Fast

Reproducible

Simple developer workflow

Cons

Newer tool than pip, smaller long-term track record.

Future Review

Review if uv adoption stalls or a superior tool emerges.

---

# ADR-022

Title

Enforce Uniqueness on OAuthAccount (provider, provider_user_id)

Status

Accepted

Context

docs/03_DATABASE_DESIGN.md §3 defines the `oauth_accounts` table but does not specify a uniqueness constraint on the combination of `provider` and `provider_user_id`.

Decision

Add a unique constraint on `(provider, provider_user_id)` in the `oauth_accounts` table.

Reason

Without this constraint, the same external OAuth identity (e.g. the same Google account) could be linked to a ClaudeTrading account more than once, or linked inconsistently across concurrent requests, producing duplicate or ambiguous account-linking records.

This is an inferred correctness requirement, not an explicit item in docs/03 - recorded here per CLAUDE.md's "never invent architecture" rule so schema decisions beyond the literal documentation stay traceable.

Trade-offs

Pros

Prevents duplicate/ambiguous OAuth identity links.

Matches standard practice for OAuth account-linking tables.

Cons

None identified; a unique constraint on this pair has no legitimate case for duplication.

Future Review

Revisit if a provider requires multiple linked identities per (provider, provider_user_id) pair (not currently anticipated).

---

# ADR-023

Title

Hash Refresh Tokens with SHA-256, Distinct from Argon2id Password Hashing

Status

Accepted

Context

docs/23_AUTHENTICATION_AND_RBAC.md §6 requires sessions to be tracked and revocable, and `UserSessionRepository.get_by_refresh_token_hash` looks up a session by an exact hash match on the presented refresh token. docs/23 does not specify a hashing algorithm for this. Argon2id (used for passwords per docs/23 §7) is salted per-hash and designed to be verified against a known plaintext, not looked up by equality - it cannot support this access pattern.

Decision

Hash refresh tokens with SHA-256 (`app.core.security.hash_token`) for storage in `UserSession.refresh_token_hash` and for lookup. Continue using Argon2id exclusively for password hashing.

Reason

Refresh tokens are high-entropy, randomly generated JWTs (not low-entropy user secrets), so a fast deterministic hash is appropriate and enables the required exact-match session lookup. Argon2id remains reserved for passwords, where slow, salted hashing defends against offline brute-force of user-chosen secrets.

Alternatives Considered

Option A: Store refresh tokens in plaintext - rejected, a database read would leak valid session tokens.

Option B: Use Argon2id for refresh tokens too - rejected, salted hashes cannot be looked up by equality without also storing the plaintext or salt separately, defeating the purpose.

Option C: SHA-256 (chosen) - deterministic, fast, appropriate for high-entropy tokens.

Trade-offs

Pros

Enables O(1) session lookup by hash.

Keeps password hashing (Argon2id) and token hashing (SHA-256) each suited to their own threat model.

Cons

SHA-256 alone would be unsuitable for low-entropy secrets; must not be reused for passwords.

Consequences

Positive

Session/refresh-token lookups remain a simple indexed equality query.

Negative

None identified; this is inferred beyond the literal text of docs/23, recorded here per CLAUDE.md's "never invent architecture" rule (same practice as ADR-022).

Future Review

Revisit if refresh tokens are ever generated with lower entropy, or if a token-revocation-by-`jti` scheme (see BACKLOG.md) replaces hash-based session lookup.

---

# Review Policy

Review ADRs:

- Before major releases
- When introducing new infrastructure
- When replacing providers
- When changing AI models
- During annual architecture reviews