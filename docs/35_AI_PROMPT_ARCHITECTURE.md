# AI Prompt Architecture

Version: 1.1

Implementation (Phase 6A): docs/50_AI_ORCHESTRATOR_ARCHITECTURE.md §7 replaces this document's skeleton with concrete content - system/user prompt text, a JSON schema for the seven-section `reasoning` output, and `PROMPT_VERSION` as a plain git-versioned string constant (no separate prompts table). "Model Routing" is not implemented in 6A - a single provider (OpenAI) and a single prompt serve the one use case this phase has; routing logic is deferred until a second real use case (e.g. AI Chat Assistant, Phase 6C) demonstrates a need for it.

---

# Objective

Standardize every AI interaction.

---

# Prompt Structure

System Prompt

↓

Context

↓

Evidence

↓

User Request

↓

Output Schema

---

# Prompt Rules

Never invent facts.

Never ignore conflicts.

Always explain reasoning.

Always return structured output.

---

# Context Builder

Technical Engine

SMC Engine

Economic Engine

News Engine

Risk Engine

Confidence Engine

---

# Output

JSON

Explanation

Warnings

Recommendation

Confidence

---

# Prompt Versioning

Version

Date

Author

Changes

---

# Model Routing

Reasoning

Summarization

Educational

Conversation

Future Multi-Agent

---

# Future

Prompt A/B Testing

Automatic Prompt Evaluation

Prompt Replay

Model Comparison