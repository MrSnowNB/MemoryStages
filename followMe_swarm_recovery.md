Below is a ready-to-drop Markdown playbook you can add as docs/FIX_CHAT_SWARM_STEPWISE.md. It’s written to “lock” an autonomous coding agent to stepwise, verifiable tasks with strict gates. It fixes the Stage 1 chat contract mismatch, API routing, and frontend base URL issue, and brings the swarm back online with safe defaults. Copy this file into your repo and run the steps in order.

Filename: docs/FIX_CHAT_SWARM_STEPWISE.md

Title: Stepwise Repair Plan: Chat + Swarm Online

Purpose

Guide an autonomous coding agent through minimal, verifiable fixes to:

Align Stage 1 /chat endpoint contract with the web UI

Ensure chat router mounts with feature flags

Make frontend API base URL resilient

Verify end-to-end via smoke tests and manual checks

Each step has a Definition of Done (DoD), Commands, and Rollback.

Rules of Engagement for the Agent

Follow steps in order. Do not skip.

After each change, run the listed tests and capture outputs.

If a DoD fails, perform the Rollback immediately, then re-apply with corrections.

Never edit files outside the Scope listed for each step.

Prerequisites

Branch: create fix/chat-swarm-restore

Runtime:

Python 3.10+

make dev runs API on 8000

make web runs web on 3000

Env: duplicate .env.example to .env and ensure:

CHAT_API_ENABLED=true

SWARM_ENABLED=false

SWARM_FORCE_MOCK=true

DEBUG=true

Step 0 — Baseline Snapshot

Scope: No code changes. Only diagnostics.

Actions:

git status; git rev-parse --short HEAD

make dev in Terminal A

make web in Terminal B

curl http://localhost:8000/health

curl http://localhost:8000/chat/health

curl -X POST http://localhost:8000/chat/message -H "Content-Type: application/json" -d '{"content":"ping","user_id":"default"}'

curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" -d '{"message":"ping","user_id":"default"}'

Open browser console at http://localhost:3000 and send “ping”

DoD:

Collect outputs with status codes and bodies (even if failing).

Save to logs/baseline_YYYYMMDD_HHMM.txt

Rollback: None.

Step 1 — Frontend API Base URL Resilience

Problem: index.html hardcodes API_BASE_URL causing cross-origin or connectivity issues when not running on localhost:8000.​

Scope: web/index.html only.

Changes:

Replace const API_BASE_URL = "http://localhost:8000" with:
const API_BASE_URL = window.location.origin.replace(":3000", ":8000");
// If already on 8000, keep as-is:
// If location is not 3000, fallback to default from ENV injection if provided.

Add a small fallback:
// Fallback if not running standard dev ports
const DEFAULT_API = "http://localhost:8000";
const resolvedAPI = (API_BASE_URL.includes(":8000") || API_BASE_URL.includes(":3000"))
? API_BASE_URL
: DEFAULT_API;
const API = resolvedAPI;

Commands:

make web (restart if already running)

From the browser: open http://localhost:3000, verify no network errors on load

DoD:

Browser network panel shows successful GET to http://localhost:8000/health when UI loads or when Status checks run.

No mixed-origin or CORS errors in console.

Rollback:

Revert web/index.html to previous revision.

Step 2 — Implement True Stage 1 Simple Chat Endpoint

Problem: Frontend Stage 1 posts {message, user_id} to /chat and expects {reply: ...}, but backend /chat currently expects SwarmMessageRequest {content,...}. This causes 422 or mishandled responses.​

Scope: src/api/main.py (or create src/api/chat_simple.py and include in main.py)

Changes:

Add a dedicated endpoint:

Path: POST /chat

Request model: {message: str, user_id: Optional[str]}

Behavior:

Log episodic event (type: "simple_chat_request")

Optional: naive intent: if message starts with “remember ”, write to KV as (key=value) or message chunk, else read attempt with best-effort lookup; however, keep it minimal and safe.

Return JSON: {reply: str, canonical: Optional[object]}

Never call the Swarm/orchestrator here.

Ensure this endpoint coexists with the chat router mounted at /chat/message and /chat/health (no path collision).

Commands:

make dev (restart server)

curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" -d '{"message":"hello","user_id":"default"}'

DoD:

200 OK with body containing reply string.

No pydantic validation error.

Rollback:

Revert changes in main.py (or delete chat_simple.py) and ensure server runs.

Step 3 — Ensure Chat Router Mounting by Feature Flag

Problem: If CHAT_API_ENABLED=false in runtime env, /chat/message and /chat/health won’t exist, breaking Swarm Mode health and mock replies.​

Scope: src/core/config.py, src/api/main.py only.

Changes:

Verify default in config: CHAT_API_ENABLED defaults true when not provided.

In main.py boot logging, print “[BOOT] CHAT_API_ENABLED={value}”.

Confirm app.include_router(chat_router, prefix="/chat") wrapped in if CHAT_API_ENABLED.

Commands:

make dev (restart)

curl http://localhost:8000/chat/health

curl -X POST http://localhost:8000/chat/message -H "Content-Type: application/json" -d '{"content":"ping","user_id":"default"}'

DoD:

/chat/health returns 200 with a JSON status payload even if degraded.

/chat/message returns mock reply when SWARM_FORCE_MOCK=true.

Rollback:

Revert router mounting changes.

Step 4 — Verify Frontend Mode Switching and Fallback

Problem: UI health panel may show “unhealthy” if /chat/health missing or degraded; send should still work via fallback.​

Scope: No code changes. Manual verification.

Actions:

With defaults (mock on), send “ping” in the UI. Confirm response arrives.

Temporarily set CHAT_API_ENABLED=false in .env and restart API:

Expected: UI health shows unhealthy, but sending falls back to /chat and still replies via Stage 1 endpoint from Step 2.

Restore CHAT_API_ENABLED=true when done.

DoD:

UI can send and receive in both modes:

Swarm Mode ON: uses /chat/message, gets response (mock)

Swarm Mode OFF or router disabled: uses /chat, gets response

Rollback:

Restore original .env and restart API.

Step 5 — Add or Update Minimal Tests

Scope: tests/ directory. Non-breaking additions.

Changes:

test_chat_simple_endpoint.py:

POST /chat with {"message":"hello","user_id":"t"} -> expect 200 and "reply" in body

test_chat_router_mock.py:

With CHAT_API_ENABLED=true, SWARM_FORCE_MOCK=true:

GET /chat/health -> 200

POST /chat/message {"content":"ping","user_id":"t"} -> 200 and expected mock shape

Commands:

make smoke or pytest -q

DoD:

Tests pass locally.

No existing tests broken.

Rollback:

Remove new tests if they conflict; re-run.

Step 6 — Swarm Bring-up (Optional, Post-Restore)

Goal: Turn on SWARM_ENABLED and connect to Ollama.

Scope: .env and minimal code touch if needed.

Actions:

Ensure Ollama has needed model: ollama pull qwen2.5:7b or per your default

Set in .env:

SWARM_ENABLED=true

SWARM_FORCE_MOCK=false

OLLAMA_MODEL set to an available model tag

Restart API and test:

curl http://localhost:8000/chat/health (should include model/ollama readiness)

UI: send a message in swarm mode

DoD:

/chat/health shows healthy with model ready.

/chat/message returns generated content, not mock.

Rollback:

Reset to SWARM_ENABLED=false, SWARM_FORCE_MOCK=true.

Step 7 — Documentation and Commit

Scope: README_WEB.md and project README where appropriate.

Changes:

Document the Stage 1 /chat contract:

POST /chat {message,user_id?} -> {reply,canonical?}

Document Swarm Mode endpoints at /chat/message and /chat/health, feature flags, and fallback behavior.

Clarify web/index.html base URL resolution and local dev expectations.

Commands:

git add -A

git commit -m "Fix: Stage 1 /chat contract + router mount + resilient web API base URL; add tests; restore swarm"

git push origin fix/chat-swarm-restore

DoD:

All manual checks green, tests passing, docs updated.

Rollback Policy

On any failure that blocks progress and cannot be corrected within the step, revert the changes in that step and restore server to running state before retrying.

Appendix: Minimal Stage 1 Endpoint Spec (for the agent)

File: src/api/main.py (or new src/api/chat_simple.py, then include in main)

Pydantic models:

class SimpleChatRequest(BaseModel): message: str; user_id: Optional[str]="default"

class SimpleChatResponse(BaseModel): reply: str; canonical: Optional[dict]=None

Endpoint:

@app.post("/chat", response_model=SimpleChatResponse)

Try/except; log episodic write

Return SimpleChatResponse(reply=f"Echo: {req.message}")

Non-goals:

Do not call swarm/orchestrator here

Do not introduce vector DB in Stage 1

Keep response schema minimal for UI compatibility

Validation Checklist After Completion

curl http://localhost:8000/health -> 200 with service info

curl http://localhost:8000/chat/health -> 200 (mock healthy or degraded)

curl -X POST http://localhost:8000/chat -d '{"message":"ping"}' -> 200 reply string

curl -X POST http://localhost:8000/chat/message -d '{"content":"ping"}' -> 200 mock or real

UI at http://localhost:3000 can send/receive in both router-enabled and router-disabled modes

Tests passing: test_chat_simple_endpoint.py, test_chat_router_mock.py

Notes for Reviewers

The plan keeps Stage 1 isolated and minimal while preserving the router-based swarm API.

Swarm can be enabled later by toggling flags without reworking the UI.

The API base URL change prevents common local dev pitfalls.