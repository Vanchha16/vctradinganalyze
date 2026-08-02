# AI Chat Architecture

# 1. Scope

Phase 6C's `AIChatEngine` (`app/services/ai_chat_engine.py`) is a conversational, read-only layer over everything Phase 4-6B already built (ADR-093/094). It answers questions about assets, explains already-decided BUY/SELL/WAIT recommendations and persisted signals, and provides general platform/educational explanations - it never computes a new recommendation, confidence score, risk level, or any other evidence field itself. Every fact referenced in a response is either reused verbatim from an existing engine's already-computed output, a persisted `ai_analysis`/`signals` row, or explicitly stated as unavailable (docs/22 §4/§13) - the assistant never invents market evidence.

See `docs/22_AI_CHAT_ASSISTANT.md` for the original product-vision document this narrows, `docs/50_AI_ORCHESTRATOR_ARCHITECTURE.md` for the AI Orchestrator being reused for grounding and for the provider abstraction being extended, and `docs/51_SIGNAL_ARCHITECTURE.md` for the Signal Engine being reused for grounding.

---

# 2. Reuse Map (ADR-093, ADR-094)

| Requirement (this phase's brief) | Reused from |
|---|---|
| Technical Analysis, SMC, Market Regime, Analysis Confidence, News Sentiment, Economic Calendar, Strategy Engine, Risk Management | `app.services.ai_orchestrator.context_builder.ContextBuilder.build(asset, timeframe)` - the exact same call `AIOrchestratorEngine` itself makes (docs/50 §3), reused unmodified |
| AI Orchestrator (explain BUY/SELL/WAIT decisions) | `AIAnalysisRepository` - the most recent persisted `ai_analysis` row for the asset/timeframe, never a new recommendation computation |
| Signal Engine (explain generated signals) | `SignalRepository` - the most recent persisted `signals` row for the asset/timeframe (Phase 6B) |
| OpenAI integration | `AIProvider` Protocol / `OpenAIProvider` (Phase 6A) - extended with one new method, not a second client (ADR-092) |
| Prompt architecture conventions | `app/services/ai_chat/chat_prompt_builder.py` - a new sibling module following `ai_orchestrator/prompt_builder.py`'s exact conventions (versioned constant, explicit guardrail system prompt, deterministic fact serialization), not a new prompt system |

No new evidence-gathering code exists anywhere in Phase 6C - `AIChatEngine` calls exactly three already-existing read paths (`ContextBuilder.build()`, `AIAnalysisRepository.find_paginated()`, `SignalRepository.find_paginated()`) and one extended provider method. This is the same reuse-first discipline as Signal Engine (docs/51 §1, ADR-085), applied one layer higher.

---

# 3. Provider Extension (ADR-092)

`AIProvider` (docs/50 §8) currently has exactly one capability: `generate()`, which always forces OpenAI's structured-output JSON-schema mode for the seven-section `reasoning` object. A conversational reply is free-text and multi-turn (system + prior turns + new question), not a single-shot structured document - reusing `generate()` as-is would mean either fabricating a fake JSON schema for prose, or bypassing the shared provider entirely and hand-rolling a second `httpx.Client` (explicitly rejected by this phase's brief).

Decision: add one new method to the same `AIProvider` Protocol and the same `OpenAIProvider` class:

```python
class AIProvider(Protocol):
    def generate(self, request: AIGenerationRequest) -> AIGenerationResponse: ...      # unchanged (Phase 6A)
    def generate_chat_reply(self, request: AIChatRequest) -> AIChatResponse: ...        # new (Phase 6C)
```

`AIChatRequest` carries a `messages: list[ChatTurn]` (role + content, covering system/user/assistant turns for multi-turn context) and `max_tokens: int` - no `json_schema` field, since chat replies are free text. `OpenAIProvider.generate_chat_reply()` shares the exact same `httpx.Client` construction (base URL, auth header, timeout, transport injection for tests) and the exact same status-code-to-exception classification as `generate()`, factored into one shared private helper (`_post_chat_completion`) so the two methods differ only in the request body they send (no `response_format`, a full message list instead of a fixed system+user pair) - the same OpenAI client, same settings, same error handling, genuinely one integration with two entry points, not two integrations.

`MockAIProvider` (test-only) gains a matching `generate_chat_reply()` for the same reason it already implements `generate()` - test injection, never used in production wiring.

---

# 4. Never Recompute a Recommendation (ADR-094)

`AIChatEngine` explains what an existing engine has already decided; it never decides anything itself. Concretely:

- "Why is this a BUY?" → the engine looks up the most recent persisted `ai_analysis` row (`AIAnalysisRepository`) for the referenced asset/timeframe and gives its `recommendation`/`reasoning`/`supporting_evidence`/`conflicting_evidence` to the model as fixed facts to explain in conversational language - exactly the same "decided fact, narrate only" boundary `AIOrchestratorEngine`'s own prompt already enforces (ADR-078/079), extended to a second consumer of that boundary.
- "Explain this signal" → the most recent persisted `signals` row (`SignalRepository`), reused the same way.
- If no persisted `ai_analysis`/`signals` row exists yet for the asset/timeframe in question, the assistant states that explicitly (docs/22 §13) - it does not fall back to computing a fresh recommendation itself (that would make Chat a second, competing entry point into recommendation logic, the exact problem Signal Engine's ADR-085 avoided for persistence).
- General/educational questions ("What is a Fair Value Gap?") need no persisted row or live evidence at all - the system prompt permits general platform/concept explanations, but the same "never invent a specific price/indicator/event value" guardrail always applies.

---

# 5. Two-Level Symbol/Timeframe Scoping (ADR-095)

docs/22 §10 ("Conversation Memory") expects the assistant to remember "current asset" and "current timeframe" across a session, while this phase's brief (§6) asks each message to store its own "referenced symbol/timeframe." Both are implemented, at two different levels:

- **Conversation-level** (`conversations.current_symbol`/`current_timeframe`, mutable): the conversation's current focus, updated whenever a message explicitly supplies a symbol/timeframe. A follow-up message that omits them inherits the conversation's current values (multi-turn continuity, docs/22 §10/§11's "Compare with GBPUSD" follow-up pattern).
- **Message-level** (`messages.symbol`/`timeframe`, immutable once written): the symbol/timeframe actually used to ground that specific exchange - an audit trail, not a live pointer, so a conversation's history remains an accurate record even after `current_symbol` later changes.

The symbol/timeframe are **client-supplied, never NLP-parsed from free text**. Extracting "EURUSD" out of "Should I trade EURUSD today?" or resolving "Gold" to `XAUUSD` would require an entity-recognition/symbol-resolution component that doesn't exist anywhere in this project and isn't specified by any document - inventing one now would violate "never invent architecture." The API request body accepts explicit optional `symbol`/`timeframe` fields (e.g. populated by a symbol picker in the calling UI) instead.

Multi-asset comparison ("Compare Gold and Silver," docs/22 §5) is out of scope for this reason too - grounding is single-symbol-per-message, mirroring News's deliberately-excluded `/multi-asset` endpoint precedent (docs/46 §12).

---

# 6. Persistence Model (ADR-096)

`conversations` and `messages` are inferred tables - `docs/03_DATABASE_DESIGN.md` had no entry for either before this phase (unlike `ai_analysis`/`signals`, which docs/03 v1.0 at least stubbed out).

## conversations

`UUIDMixin` + `TimestampMixin` (not `CreatedAtMixin` - `current_symbol`/`current_timeframe`/`title`/`status` are all mutated after creation, unlike every append-only table in this project).

| Field | Notes |
|---|---|
| `id` | |
| `user_id` | FK `users.id`, cascade - conversations are private, per-user |
| `title` | nullable, auto-derived from the first user message (first ~60 chars) |
| `current_symbol` | nullable - the conversation's current asset focus (§5) |
| `current_timeframe` | nullable |
| `status` | `ACTIVE` / `ARCHIVED` (ADR-097) |
| `created_at`, `updated_at` | |

## messages

`UUIDMixin` + `CreatedAtMixin` (append-only - a message, once sent, is never edited).

| Field | Notes |
|---|---|
| `id` | |
| `conversation_id` | FK `conversations.id`, cascade |
| `role` | `USER` / `ASSISTANT` |
| `content` | the question or the reply text |
| `symbol` | nullable, this message's referenced asset (§5) |
| `timeframe` | nullable |
| `ai_analysis_id` | nullable FK `ai_analysis.id`, `ON DELETE SET NULL` - the analysis this reply grounded itself in, if any |
| `signal_id` | nullable FK `signals.id`, `ON DELETE SET NULL` - the signal this reply grounded itself in, if any |
| `model_name` | nullable - which model produced this row (`null` for `USER` rows), docs/22 §14's "Model Version" logging requirement |
| `prompt_version` | nullable, `null` for `USER` rows - mirrors `ai_analysis.prompt_version` (ADR-018 "Version Everything") |
| `created_at` | |

`ai_analysis_id`/`signal_id` use `ON DELETE SET NULL` (not `CASCADE`) - a message is a historical conversational record; the underlying analysis/signal being referenced is (Phase 6A/6B are append-only and never delete) effectively permanent, but if either table's retention policy ever changes, a message should outlive the row it once referenced rather than being destroyed by an unrelated cleanup.

---

# 7. Data Flow

```
AIChatEngine.send_message(conversation, content, symbol=None, timeframe=None)
  -> resolve effective symbol/timeframe: explicit args, else conversation.current_symbol/current_timeframe
  -> if symbol resolved:
       asset = asset_repository.get_by_symbol(symbol)                    [404 if unknown]
       context = context_builder.build(asset, timeframe)                  [reused verbatim, docs/50 §3]
       latest_analysis = ai_analysis_repository.find_paginated(asset_id, timeframe, limit=1)[0] or None
       latest_signal = signal_repository.find_paginated(asset_id, timeframe, limit=1)[0] or None
       conversation.current_symbol, .current_timeframe = symbol, timeframe   [update "current" state]
     else:
       context = latest_analysis = latest_signal = None                  [general/educational question]
  -> history = message_repository.list_recent(conversation.id, limit=settings.chat_max_history_messages)
  -> chat_prompt_builder.build(history, content, context, latest_analysis, latest_signal)
       -> AIChatRequest(messages=[...], max_tokens=...)
  -> provider.generate_chat_reply(request)                                [one retry on transient failure, ADR-081's precedent reused]
       -> on repeated failure: deterministic apology fallback, never a hard failure surfaced to the caller
  -> persist Message(role=USER, content, symbol, timeframe)
  -> persist Message(role=ASSISTANT, content=reply, symbol, timeframe, ai_analysis_id, signal_id, model_name)
  -> return the assistant Message
```

`ContextBuilder`/`AIAnalysisRepository`/`SignalRepository` are each called **at most once** per `send_message()` call - no engine is invoked twice, mirroring every prior phase's chaining discipline (ADR-049's precedent, continued through AI Orchestrator §3 and Signal Engine).

---

# 8. Conversation Lifecycle (ADR-097)

Both **archive** and **hard delete** are supported, since this phase's brief explicitly asks for "delete/archive":

- `POST /chat/conversations/{id}/archive` - soft, sets `status=ARCHIVED`; excluded from `GET /chat/conversations`' default listing but still retrievable by id. Reversible in principle (a future `unarchive` action), matches this project's general preference for status-transition over destruction (`SMCEvent`, `EconomicEvent`).
- `DELETE /chat/conversations/{id}` - hard delete, cascades to every `messages` row. Offered because conversations are private user data (unlike audit logs or market evidence, which this project never lets users delete) - a user should be able to genuinely remove their own conversation history, not merely hide it.

---

# 9. API (ADR-092 through ADR-097)

All routes require authentication (`get_current_user`) - conversations are private per-user data, and generating a reply calls the same metered LLM provider as Phase 6A (same cost rationale as ADR-083).

```
POST   /chat/conversations                          create a conversation (optionally seeded with symbol/timeframe)
GET    /chat/conversations?status=&page=&limit=      list the current user's conversations (ACTIVE by default)
GET    /chat/conversations/{id}                       conversation detail + its messages
POST   /chat/conversations/{id}/messages              send a message, get the assistant's reply
POST   /chat/conversations/{id}/archive                soft-archive
DELETE /chat/conversations/{id}                        hard delete (cascades messages)
```

`POST /chat/conversations/{id}/messages` request:

```json
{ "content": "Why is this a BUY?", "symbol": "EURUSD", "timeframe": "h1" }
```

`symbol`/`timeframe` are optional - omitted, the conversation's current values are used; if neither is ever set, the question is treated as general/educational (§4/§5).

Response: the persisted assistant `Message` (id, role, content, symbol, timeframe, ai_analysis_id, signal_id, model_name, created_at) plus the persisted user `Message` that prompted it, and the conversation's (possibly just-updated) `current_symbol`/`current_timeframe`.

---

# 10. Testing Strategy

| File | Covers |
|---|---|
| `test_ai_chat_openai_provider.py` | `generate_chat_reply()` via `httpx.MockTransport` - success, transient/permanent failure classification, shares the transport-building path with `test_ai_openai_provider.py`'s existing coverage |
| `test_ai_chat_prompt_builder.py` | Grounded-context serialization, history inclusion, general-question (no context) path, missing-data statements |
| `test_ai_chat_engine.py` | Symbol resolution (explicit arg vs. conversation default vs. none), `ContextBuilder`/repositories called at most once, message persistence, graceful fallback on provider failure, using a fake provider (mirrors Signal Engine's `test_signal_engine.py` precedent - a thin orchestration layer doesn't need the full upstream engine stack to unit test its own wrapping logic) |
| `test_conversation_models.py` | FK cascade (delete) vs. `SET NULL` (`ai_analysis_id`/`signal_id`) behavior |
| `test_ai_chat_routes.py` | auth required, 404s, create/list/get/archive/delete, message send round-trip |

Verified by inspection, consistent with every prior phase - coverage tooling is still not installed (BACKLOG.md §4).

---

# 11. Out of Scope for Phase 6C (ADR-098 and others)

NLP symbol extraction from free text (§5); multi-asset comparison; feedback rating (`Helpful`/`Not Helpful`/`Report Issue`, docs/22 §15) - no endpoint was specified for it and it needs its own design pass (what does "improve future prompts" mean concretely?); "Question Type"/"Engines Used" classification logging (docs/22 §14) - would require a taxonomy that doesn't exist anywhere in this project; voice/chart-screenshot/PDF/multi-language/portfolio features (docs/22 §18, explicitly "Future Enhancements" even in the original vision doc); response caching (no caching precedent anywhere in this project for LLM output, docs/50 §10's reasoning applies identically here); real rate-limiting/quota infrastructure beyond authentication (same gap tracked for Phase 6A, BACKLOG.md §20).
