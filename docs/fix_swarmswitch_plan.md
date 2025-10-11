---
id: fix-swarmswitch-001
title: Re-enable Swarm Mode with UI Toggle and Preserve Stage 1
owner: cline
status: completed
created: 2025-10-11
version: 0.1
---

# Fix Plan (Swarm Switch)

## progress

```yaml
completed_tasks: [T1]
notes: |
  T1 completed: CHAT_API_ENABLED=true in .env, chat router included in FastAPI, /chat/message modified to return mock orchestrator response for general queries.

  T1 fixes made:
  - Fixed pydantic protected namespace warning in ChatMessageResponse by removing model_config (ConfigDict was added but causing issues)
  - Updated .env with CHAT_API_ENABLED=true for explicit enable
  - Modified chat.py sendChatMessage() to return mock MockResult with orchestrator_type: "rule_based", agents_consulted: [], etc.

  T2 completed: Web UI already had swarm mode toggle, defaults OFF. Toggle OFF uses /chat, ON uses /chat/message.

  T3 completed: UI banner now shows "Swarm Mode (X agents)" when enabled, displaying agent count from health response.

  T4 completed: Web server (--api-url arg) injects API base URL into HTML; frontend reads dynamic API_BASE_URL.

  T5 completed: docs/API_QUICKSTART.md updated with examples for both POST /chat and POST /chat/message endpoints.
```

## objectives

```yaml
primary: "Add Swarm Mode to web UI; keep Stage 1 simple chat default"
secondary:
  - "Feature-flag /chat/message orchestrator path"
  - "Keep POST /chat as Stage 1 path"
  - "Add clear UI mode indicator and health"
```

## assumptions

```yaml
backend: "FastAPI at http://localhost:8000"
frontend: "Web UI at http://localhost:3000"
db: "SQLite file at ./data/memory.db"
ollama: "Available locally if swarm enabled"
```

## env_flags

```yaml
CHAT_API_ENABLED: "true|false"
SWARM_ENABLED: "true|false"
VECTOR_ENABLED: "true|false"
OLLAMA_MODEL: "llama3|qwen|custom"
NEXT_PUBLIC_API_BASE: "http://localhost:8000"
```

## tasks

```yaml
- id: T1_create_router
  description: "Ensure chat router is included behind CHAT_API_ENABLED"
  files:
    - src/api/main.py
    - src/api/chat.py
  acceptance_criteria:
    - "When CHAT_API_ENABLED=true, /chat/message returns 200 with mock orchestrator"
- id: T2_add_ui_toggle
  description: "Add 'Swarm Mode' toggle in web UI; default OFF"
  files:
    - web/index.html
  acceptance_criteria:
    - "Toggle OFF → POST /chat used"
    - "Toggle ON → POST /chat/message used"
- id: T3_status_banner
  description: "UI banner indicates mode and health"
  files:
    - web/index.html
  acceptance_criteria:
    - "Shows Stage 1 Simple or Swarm Mode with agent count when ON"
- id: T4_env_wiring
  description: "Read API base from NEXT_PUBLIC_API_BASE; wire flags"
  files:
    - web/index.html
    - src/core/config.py
  acceptance_criteria:
    - "Fetches use env base; build respects flags"
- id: T5_docs_update
  description: "Update docs/API_QUICKSTART.md to document both paths"
  files:
    - docs/API_QUICKSTART.md
  acceptance_criteria:
    - "Examples include POST /chat and POST /chat/message"
```

## test_plan

```yaml
api:
  - name: health
    steps:
      - GET /health → 200
      - If CHAT_API_ENABLED=true: GET /chat/health → 200 or degraded but present
  - name: simple_chat
    steps:
      - POST /chat {message:"what is my name", user_id:"default"} → name reply
  - name: orchestrated_chat
    precondition: "CHAT_API_ENABLED=true and SWARM_ENABLED=true"
    steps:
      - POST /chat/message with bearer token (if required) → 200 and metadata with orchestrator_type
ui:
  - name: default_mode
    mode: "Toggle OFF"
    steps:
      - Send "what is my name" → reply from canonical KV
  - name: swarm_mode
    mode: "Toggle ON"
    steps:
      - Send "what is my name" → reply and orchestration metadata shown (or banner indicating swarm engaged)
```

## rollback

```yaml
steps:
  - "Revert UI toggle to OFF by default"
  - "Set CHAT_API_ENABLED=false in .env"
  - "Ensure web calls POST /chat only"
```

## signoff

```yaml
gate:
  - "All acceptance_criteria passed"
  - "docs/API_QUICKSTART.md updated"
  - "CHANGELOG.md updated"
  - "Smoke tests green"
