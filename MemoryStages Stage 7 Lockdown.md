---
title: "MemoryStages Stage 7 Lockdown - MVP Swarm/Rule-Based Orchestrator"
stage: 7
version: 1.0.0
maintainer: "MrSnowNB"
date: 2025-10-11
description: |
  This document enforces a strict staged-gate protocol for Stage 7 of MemoryStages.
  MVP focus: local, privacy-protected, rule-based agent chatbot swarm
  Each slice is isolated, fully testable, peer reviewed, rollback friendly, and only progressed upon gate clearance.
---

# 🚦 Stage 7 Lockdown Protocol & Stepwise Plan

> **Goal:** Build a privacy-locked, rule-based Python orchestrator managing a 4+ Ollama (liquid-rag:latest) local bot swarm, with hard memory adapter validation and full logs, ready for MVP human/frontend use.

---

## Stage-Gate Principles (Inspiration)
- **Scope Strictness:** Each stage is opt-in and feature-flagged. No work on future stages until current gate is approved.
- **Tests:** Every step is validated by automated and human/peer checklist tests.
- **Audit/Logging:** Every major action, key output, and decision is logged for compliance and rollback.
- **Rollback:** All partial progress must be easily reverted.

---

# 🔢 Stepwise Execution Plan

## 0. **Review/Refactor & Checklist**
- [ ] All past code meets lock scope and checklists (`docs/STAGE_CHECKS.md`)
- [ ] Pass all smoke/regression tests
- [ ] Remove any out-of-scope/forward-looking code

---

## 1. **Orchestrator & Swarm Boot**
**Files:**  
`src/agents/orchestrator.py`, `src/agents/registry.py`, `src/agents/ollama_agent.py`, `src/agents/agent.py`, `src/core/config.py`

**Tasks:**
- Set global `OLLAMA_MODEL` (only place for model swap).
- Build Python rule-based orchestrator: collects N agent replies, selects best via rules.
- Registry: spawns/tracks 4+ Ollama bots, logs all actions.

**Tests:**
- [ ] Agent registry/creation
- [ ] Orchestrator decision logic
- [ ] Model swap triggers NO code changes, just config/env edit

**Gate:** All registry/orchestrator tests pass; log review; model swap confirmed by manual and automated test.

---

## 2. **Memory Adapter & Response Validation**
**Files:**  
`src/agents/memory_adapter.py`, `tests/test_memory_adapter.py`

**Tasks:**
- All agent memory accesses routed through adapter.
- Adapter enforces: privacy, tombstone, scam/PII/sensitive keyword filter.
- Every response validated: must map to memory, otherwise prompt for user clarification.

**Tests:**
- [ ] Functional, adversarial (PII/hallucination) test
- [ ] Logs prove "no unvalidated output ever reaches user"
- [ ] Manual admin review for edge cases

**Gate:** Test suite passes, manual log/code check.

---

## 3. **/chat API & Message Flow**
**Files:**  
`src/api/chat.py`, `src/api/schemas.py`, `tests/test_chat_api.py`

**Tasks:**
- Feature-flag `/chat` endpoint.
- Validate/pipeline: user prompt → orchestrator → memory adapter → (validated) answer only.
- Schema validation for all endpoints.
- End-to-end curl & demo test.

**Tests:**
- [ ] Full integration test: user in → answer/log out, every cross-check enforced
- [ ] Prompt injection and schema tests

**Gate:** API endpoints function and log correctly; demo script runs E2E.

---

## 4. **(Optional) Plugin/Tool Layer**
**Files:**  
`src/agents/plugins.py`, `tests/test_agent_plugins.py`  
*(skip for MVP speed, or just implement math plugin if time)*

**Tasks:**
- If added, all plugin calls go through orchestrator, never access memory/DB or file system directly.

**Tests:**
- [ ] Plugin test
- [ ] Security/validation boundaries

**Gate:** Disabled by default, all plugin tests and logs pass if enabled.

---

## 5. **Session, Log Review, & Model Swap Docs**
**Files:**  
`src/core/session.py`, `tests/test_session.py`, `docs/FRONTEND_API_CONTRACT.md`, `.env.example`, `docs/MODEL_SWAPPING.md`, `examples/chat_demo.py`

**Tasks:**
- Add simple expiring session/tokens.
- Central audit/log review, easiest possible workflow (list, view, clear).
- Docs: one line to change `OLLAMA_MODEL` and swap entire stack.
- Demo script: prove chat cycle, log, and swap all work "as expected".

**Tests:**
- [ ] Sessions/logs work
- [ ] Model swap works, docs match code
- [ ] Demo script E2E

**Gate:** Everything above green, manual end-to-end check, documentation complete.

---

# ☑️ Global Delivery Checklist

- [ ] All code and docs pass each gate before progressing.
- [ ] All API/chat responses memory-validated or clarified.
- [ ] Logs show full round-trip for all orchestrator and API actions.
- [ ] Model change needs only one variable edit and restart.
- [ ] Privacy, audit, and rollback confirmed.
- [ ] Demo/test scripts run and produce correct logs/outputs.

---

**Inspired by**: MemoryStages staged-gate lockdowns, with enhancements for MVP velocity, security, and complete human oversight.

---

