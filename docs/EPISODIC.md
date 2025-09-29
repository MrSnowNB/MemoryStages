# Stage 5: Episodic & Temporal Memory

This document describes the Stage 5 episodic memory implementation, providing enhanced conversation tracking, temporal memory, and session-based retrieval capabilities.

## Overview

Episodic memory captures conversation events in a structured, queryable format with full temporal awareness. This enables session management, conversation summarization, and long-term memory analysis.

## Schema

Episodic events are stored in the `episodic` table with the following fields:

```sql
CREATE TABLE episodic (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,  -- User-scoped memory
    session_id TEXT,        -- Conversation session tracking
    ts DATETIME DEFAULT CURRENT_TIMESTAMP,
    event_type TEXT,        -- 'user', 'ai', 'system', 'agent'
    message TEXT,           -- Full message content
    summary TEXT,           -- Optional summary/abstract
    sensitive BOOLEAN DEFAULT FALSE,
    actor TEXT,             -- Backward compatibility
    action TEXT,            -- Backward compatibility
    payload TEXT            -- Backward compatibility (JSON)
);
```

### Event Types

- **`user`**: User messages from chat interactions
- **`ai`**: AI responses and generated content
- **`system`**: System events, configuration changes, errors
- **`agent`**: Agent-specific actions and decisions

### Sensitive Content Detection

Events are automatically flagged as sensitive if content contains patterns like:
- `password`, `token`, `auth`, `credentials`, `secret`
- Numeric patterns resembling keys/hashes
- High-density special character content

## API Endpoints

### POST /episodic/event

Logs a new episodic event.

```bash
curl -X POST http://localhost:8000/episodic/event \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "default",
    "session_id": "session_123",
    "event_type": "user",
    "message": "Hello, I love hiking and espresso",
    "summary": "User greeting with preferences"
  }'
```

**Response:**
```json
{
  "ok": true,
  "message": "Episodic event logged successfully"
}
```

### GET /episodic/recent

Retrieves recent episodic events with advanced filtering.

```bash
# Get recent events for user
curl http://localhost:8000/episodic/recent

# Filter by session
curl http://localhost:8000/episodic/recent?session_id=session_123

# Filter by event type
curl http://localhost:8000/episodic/recent?event_type=user&limit=10

# Filter by time range
curl http://localhost:8000/episodic/recent?since=2025-01-01T00:00:00Z
```

**Parameters:**
- `session_id` (str): Filter by conversation session
- `event_type` (str): Filter by event type ('user', 'ai', 'system', 'agent')
- `since` (str): ISO datetime or unix timestamp for temporal filtering
- `limit` (int): Max events to return (max 200)

**Response:**
```json
{
  "events": [
    {
      "id": 123,
      "user_id": "default",
      "session_id": "session_123",
      "timestamp": "2025-01-15T14:30:00Z",
      "event_type": "user",
      "message": "Set my displayName to Alice",
      "summary": null,
      "sensitive": false,
      "type": "user",
      "content": "Set my displayName to Alice"
    }
  ],
  "count": 1,
  "filters": {
    "session_id": null,
    "event_type": null,
    "since": null,
    "limit": 50
  }
}
```

### POST /episodic/summarize

Generates conversation summaries from event sequences.

```bash
curl -X POST http://localhost:8000/episodic/summarize \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "default",
    "session_id": "session_123",
    "limit": 100,
    "use_ai": false
  }'
```

**Response:**
```json
{
  "summary": "Summary of 5 events from 2025-01-15 14:30 to 14:35: 3 user input(s), 2 AI response(s). Topics covered: conversation setup.",
  "parameters": {
    "session_id": "session_123",
    "since": null,
    "limit": 100,
    "use_ai": false
  },
  "method": "text"
}
```

### GET /episodic/sessions

Lists recent conversation sessions with statistics.

```bash
curl http://localhost:8000/episodic/sessions?limit=10
```

**Response:**
```json
{
  "sessions": [
    {
      "session_id": "session_123",
      "event_count": 20,
      "user_messages": 10,
      "ai_messages": 8,
      "system_messages": 2,
      "start_time": "2025-01-15T14:30:00Z",
      "end_time": "2025-01-15T15:00:00Z",
      "sensitive_events": 0
    }
  ],
  "count": 1,
  "description": "Shows recent conversation sessions with basic statistics"
}
```

## Chat Integration

### Automatic Event Logging

All chat interactions are automatically logged as episodic events:

- **User messages**: Logged immediately upon receipt with `event_type="user"`
- **AI responses**: Logged after generation with `event_type="ai"`
- **Preference detection**: Additional events for parsed preferences
- **Session tracking**: Consistent `session_id` across conversation

### Summarize Intent Detection

Chat messages can trigger episodic summarization:

- Patterns like "Summarize our conversation" or "Tell me what we've discussed"
- Bypasses general LLM routing for deterministic episodic data
- Returns summary with `agents_consulted=0`

## Privacy and Security

### Data Privacy Rules

- **Sensitive content redaction**: Sensitive events excluded from summaries
- **Access control**: Privacy checks on event retrieval
- **Audit logging**: All episodic operations logged for compliance
- **User scoping**: All data isolated by `user_id`

### Privacy Enforcement Flags

Controlled by `.env` settings:
- `PRIVACY_ENFORCEMENT_ENABLED=true`: Enables sensitive content filtering
- Sensitive events require access validation for retrieval
- Automatic detection of sensitive patterns in messages

## Usage Examples

### Basic Session Tracking

```bash
# Log a user preference
curl -X POST http://localhost:8000/episodic/event \
  -d '{"session_id": "user_123_session", "event_type": "preference_detected", "message": "User likes hiking"}'

# Check session history
curl http://localhost:8000/episodic/recent?session_id=user_123_session
```

### Conversation Analysis

```bash
# Get chat statistics
curl http://localhost:8000/episodic/sessions?limit=5

# Generate summary for yesterday's conversations
curl -X POST http://localhost:8000/episodic/summarize \
  -d '{"since": "2025-01-14T00:00:00Z", "limit": 200}'
```

### Chat-Based Integration

```bash
# Chat flow with memory
curl -X POST http://localhost:8000/chat/message \
  -d '{"content": "Set my favorite color to blue", "user_id": "alice"}'

curl -X POST http://localhost:8000/chat/message \
  -d '{"content": "Summarize our session so far", "user_id": "alice"}'
# Returns episodic-based summary, not LLM hallucination
```

## Teaching and Demo Flows

### Basic Preference Learning

1. User says: "I love hiking and expresso"
2. System detects preferences, stores in KV, logs episodic events
3. Later asks: "What do I do for fun?"
4. System retrieves from semantic/KV memory with episodic provenance

### Session Summarization Demo

1. Multi-turn conversation with KV writes and semantic preferences
2. User says: "Summarize our session so far"
3. System returns episodic-generated summary showing:
   - Preferences captured
   - Memory operations performed
   - Conversation topics without LLM invention

## Troubleshooting

### Common Issues

**404 on episodic routes:**
- Check router mounting: `app.include_router(episodic_router, prefix="/episodic", tags=["episodic"])`
- Restart server after adding router

**Empty summaries:**
- Verify episodic table has data: `sqlite3 data/memory.db "SELECT COUNT(*) FROM episodic"`
- Check `user_id` consistency across requests

**Sensitive data exposed:**
- Verify `PRIVACY_ENFORCEMENT_ENABLED=true` in `.env`
- Check privacy audit logs for access violations

### Debug Commands

```bash
# Check episodic data
sqlite3 data/memory.db "SELECT event_type, message FROM episodic ORDER BY ts DESC LIMIT 10"

# Verify router mounting
curl http://localhost:8000/docs | grep -i episodic

# Test sensitive filtering
curl http://localhost:8000/episodic/recent  # Should redact sensitive events
```

## Maintenance

### Data Cleanup

```bash
# Remove old session data (90 days)
python3 -c "
from src.core.db import get_db
with get_db() as conn:
    conn.execute('DELETE FROM episodic WHERE ts < datetime(\"now\", \"-90 days\")')
    conn.commit()
"
```

### Performance Monitoring

- Episodic table size: `SELECT COUNT(*) FROM episodic`
- Query performance: Indexes on `user_id, session_id, ts, event_type`
- Summarization runtime should be < 100ms for 50 events

## Related Documentation

- `docs/STAGE_CHECKS.md`: Stage 5 validation checklist
- `docs/PRIVACY.md`: Data privacy procedures
- `docs/API_QUICKSTART.md`: Complete API reference
- `tests/test_episodic.py`: Episodic testing examples
