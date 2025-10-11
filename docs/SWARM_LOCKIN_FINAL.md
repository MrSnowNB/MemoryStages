Title: SWARM Lock-In: Final Stepwise Recovery Plan

Core rules for bots

Follow steps in exact order.

After every code change, run the required checks.

If a DoD fails, roll back immediately and retry.

Never change endpoint contracts defined below.

Never "optimize" steps or combine them.

Baseline contracts and flags

Stage 1 Simple Chat

POST /chat

Request: {"message": "str", "user_id": "str?"}

Response: {"reply": "str", "canonical": "object?"}

Swarm Chat Router

POST /chat/message

Request: {"content": "str", "user_id": "str?"}

Response: JSON with content/model_used/metadata

Health

GET /health → overall server health and DB info

GET /chat/health → swarm/agent/memory readiness

Required flags (.env)

CHAT_API_ENABLED=true

SWARM_ENABLED=true

SWARM_FORCE_MOCK=false

VECTOR_ENABLED=true

OLLAMA_MODEL=qwen2.5:3b-instruct (or liquid-rag:latest)

DEBUG=true

Step 0 — Freeze context and branch

Actions:

git checkout -b fix/swarm-lockin-final

git status; git rev-parse --short HEAD

DoD:

On branch fix/swarm-lockin-final

Rollback:

git checkout main; git branch -D fix/swarm-lockin-final

Step 1 — Establish hard tests to prevent drift

Create tests:

tests/test_chat_simple_endpoint.py

POST /chat {"message":"ping","user_id":"t"} → 200 and "reply" in body

tests/test_chat_router_health_and_send.py

GET /chat/health → 200 and JSON with status key

POST /chat/message {"content":"ping","user_id":"t"} → 200 (even if mock)

Commands:

pytest -q or make smoke

DoD:

Tests added and run (they may fail now; that's expected)

Rollback:

git rm the new tests

Step 2 — Fix async/await misuse in chat router

Scope: src/api/chat.py and any orchestrator helpers it calls

Actions:

Search for awaits on booleans:

grep/rg for patterns: "await .*ENABLED", "await .*MOCK", "await .*adapter", "await .*ready"

Replace improper awaits:

If a flag is a bool (e.g., config.SWARM_ENABLED), never await it

If a helper now returns bool and is not async, remove await

Re-run tests after change

Commands:

make dev (restart)

pytest -q

curl -X POST http://localhost:8000/chat/message -H "Content-Type: application/json" -d '{"content":"ping","user_id":"default"}'

DoD:

POST /chat/message returns 200 (mock or real), not 500

No "object bool can't be used in 'await' expression" in logs

Rollback:

git checkout HEAD^ -- src/api/chat.py and related helpers

Step 3 — Memory adapter readiness to remove "degraded"

Scope: wherever /chat/health is composed (likely src/api/chat.py or health helper)

Actions:

Ensure VECTOR_ENABLED=true in .env

Initialize or stub a MemoryAdapter with is_ready() → True when VECTOR_ENABLED=true

If FAISS isn't fully implemented, create a stub adapter that returns ready=True and empty results

Ensure /chat/health sets memory_adapter_enabled=true iff adapter is ready

Commands:

make dev

curl http://localhost:8000/chat/health

DoD:

GET /chat/health returns {"status":"healthy"} when Ollama is healthy and memory_adapter_enabled=true

Rollback:

Revert memory adapter changes; keep SWARM_DISABLED to stabilize

Step 4 — Enforce router mount and simple endpoint coexistence

Scope: src/api/main.py (mount logic), src/api/chat.py (router)

Actions:

Ensure app.include_router(chat_router, prefix="/chat") is executed only when CHAT_API_ENABLED=true

Ensure a separate simple Stage 1 handler exists:

POST /chat with SimpleChatRequest(message,user_id?) → SimpleChatResponse(reply,canonical?)

Confirm there's no path collision with /chat/message

Commands:

make dev

curl http://localhost:8000/chat/health

curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" -d '{"message":"ping"}'

curl -X POST http://localhost:8000/chat/message -H "Content-Type: application/json" -d '{"content":"ping"}'

DoD:

Both endpoints return 200

/chat/health exists and reports healthy

Rollback:

Revert main.py router and simple endpoint deltas

Step 5 — Lock flags to "real swarm" with a small model

Scope: .env only

Actions:

Set:

CHAT_API_ENABLED=true

SWARM_ENABLED=true

SWARM_FORCE_MOCK=false

VECTOR_ENABLED=true

OLLAMA_MODEL=qwen2.5:3b-instruct (or liquid-rag:latest)

DEBUG=true

Ensure Ollama has the model:

Verify via http://localhost:11434/api/tags (you have qwen2.5:3b-instruct and liquid-rag:latest listed)

Commands:

make dev

curl http://localhost:8000/chat/health

curl -X POST http://localhost:8000/chat/message -H "Content-Type: application/json" -d '{"content":"ping","user_id":"default"}'

DoD:

/chat/health shows healthy

/chat/message returns generated content (not mock)

Rollback:

Set SWARM_ENABLED=false and SWARM_FORCE_MOCK=true to regain stability

Step 6 — Web UI mode verification and API base

Scope: web/index.html only

Actions:

Ensure API base resolves to the API reliably:

const DEFAULT_API = "http://localhost:8000";

const API_BASE = window.location.origin.replace(":3000", ":8000");

const API = API_BASE.includes(":8000") ? API_BASE : DEFAULT_API;

Health panel message:

If /chat/health healthy → show "Swarm Mode Active"

If degraded or 404 → show "Swarm unavailable; using Stage 1"

Send logic:

Swarm Mode: POST /chat/message; on 404/500 fallback once to /chat and mark fallback-used=true in UI footer

Commands:

make web

In browser, send "ping"

DoD:

UI shows Swarm Mode Active and uses /chat/message; responses appear with swarm metadata

Rollback:

Restore previous index.html

Step 7 — Tests become mandatory for merges

Scope: Makefile/CI scripts and tests/

Actions:

Ensure make smoke or pytest -q runs:

tests/test_chat_simple_endpoint.py

tests/test_chat_router_health_and_send.py

Add a pre-commit or simple CI script in scripts/run_tests.sh

DoD:

Tests pass locally; merges depend on tests

Rollback:

Temporarily disable pre-commit, but only if absolutely necessary

Step 8 — Final verification checklist

Commands:

curl http://localhost:8000/health → healthy with kv_count

curl http://localhost:8000/chat/health → healthy, memory_adapter_enabled:true, model shows

curl -X POST /chat {"message":"ping"} → reply string

curl -X POST /chat/message {"content":"ping"} → generated content

Browser: http://localhost:3000 shows "Swarm Mode Active", sending works via router

pytest -q → all green

DoD:

All checks green simultaneously

Hard guardrails to prevent future drift

Do not change /chat and /chat/message request/response schemas without updating tests first.

Never await feature flags or booleans again.

If memory adapter is temporarily stubbed, keep VECTOR_ENABLED=true and is_ready() → True; document this in docs/ for Stage 2 work.

Keep OLLAMA_MODEL as a small, reliable tag in .env until performance tuning is planned.

Known pitfalls and quick resolutions

500 with "object bool can't be used in 'await' expression"

Action: remove await from flag/bool checks in chat router/orchestrator

"degraded" even when Ollama is healthy

Action: memory_adapter_enabled must reflect a real or stub adapter that reports ready

UI shows red while Stage 1 works

Action: ensure /chat/health returns healthy once memory adapter is ready and SWARM_ENABLED=true; else the UI should clearly show a Stage 1 fallback banner

Finish and commit sequence

git add -A

git commit -m "fix(swarm): remove async misuse, enable memory adapter readiness, lock endpoints; tests added"

git push -u origin fix/swarm-lockin-final

If you want, I can produce the exact code snippets for:

Removing the await misuse in src/api/chat.py

Adding a MinimalMemoryAdapter stub

Adding tests test_chat_simple_endpoint.py and test_chat_router_health_and_send.py

The UI API base and health banner edits
