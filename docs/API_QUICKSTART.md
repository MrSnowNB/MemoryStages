# MemoryStages API Quickstart

This document provides quick examples for interacting with the MemoryStages API.

**Important**: Vector search features described below are BETA and disabled by default. Enable with `SEARCH_API_ENABLED=true`.

## Starting the Server

```bash
# Default configuration (Stage 1 only)
make dev

# With vector search enabled
SEARCH_API_ENABLED=true VECTOR_ENABLED=true make dev
```

## Basic KV Operations

### Create/Update a Key

```bash
curl -X PUT "http://localhost:8000/kv" \
  -H "Content-Type: application/json" \
  -d '{
    "key": "favorite_color",
    "value": "blue",
    "source": "user_input",
    "casing": "lower",
    "sensitive": false
  }'
```

### Get a Key

```bash
curl "http://localhost:8000/kv/favorite_color"
```

### List All Keys

```bash
curl "http://localhost:8000/kv/list"
```

### Delete a Key

```bash
curl -X DELETE "http://localhost:8000/kv/favorite_color"
```

## Episodic Events

### Add an Event

```bash
curl -X POST "http://localhost:8000/episodic" \
  -H "Content-Type: application/json" \
  -d '{
    "actor": "user",
    "action": "create_key",
    "payload": "User set favorite_color to blue"
  }'
```

### List Events

```bash
curl "http://localhost:8000/episodic"
```

## Semantic Search (BETA)

**Note**: This endpoint is feature-flagged and returns 404 when `SEARCH_API_ENABLED=false`.

### Basic Search

```bash
curl "http://localhost:8000/search?query=blue&k=5"
```

### Search with Specific Limit

```bash
curl "http://localhost:8000/search?query=user+colors&k=3"
```

Response format:
```json
{
  "results": [
    {
      "key": "favorite_color",
      "value": "blue",
      "score": 0.9,
      "casing": "lower",
      "source": "user_input",
      "updated_at": "2025-01-26T12:00:00Z"
    }
  ]
}
```

## Health Check

```bash
curl "http://localhost:8000/health"
```

## Debug Endpoint

**Note**: Only available when `DEBUG=true`.

```bash
curl "http://localhost:8000/debug"
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_PATH` | `./data/memory.db` | SQLite database location |
| `DEBUG` | `true` | Enable debug features and logging |
| `VECTOR_ENABLED` | `false` | Enable vector memory overlay |
| `VECTOR_PROVIDER` | `memory` | Vector store type (memory/faiss) |
| `EMBED_PROVIDER` | `hash` | Embedding provider (hash for testing) |
| `SEARCH_API_ENABLED` | `false` | Enable semantic search endpoint |

## BETA Feature Warnings

The semantic search endpoint is experimental and may be removed or modified. It consumes additional resources and defaults to disabled. Results are not persisted across restarts when using in-memory vector storage.
