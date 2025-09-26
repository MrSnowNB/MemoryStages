# API Quick Start Guide

This document provides curl examples for testing all Stage 1 endpoints. Use these for manual validation and smoke testing.

## Prerequisites
```bash
# Start the development server
make dev

# Server runs on http://localhost:8000
# Swagger docs available at: http://localhost:8000/docs (if DEBUG=true)
```

## Health Check
```bash
curl -X GET http://localhost:8000/health

# Expected response:
# {
#   "status": "ok",
#   "version": "1.0.0-stage1", 
#   "db_ok": true,
#   "kv_count": 0,
#   "timestamp": "2024-01-01T12:00:00.000000"
# }
```

## Set KV Pairs
```bash
# Set displayName with user source
curl -X PUT http://localhost:8000/kv \
  -H "Content-Type: application/json" \
  -d '{"key":"displayName","value":"Mark","source":"user"}'

# Set favorite color
curl -X PUT http://localhost:8000/kv \
  -H "Content-Type: application/json" \
  -d '{"key":"favorite_color","value":"Purple","source":"user"}'

# Set sensitive data
curl -X PUT http://localhost:8000/kv \
  -H "Content-Type: application/json" \
  -d '{"key":"api_key","value":"secret123","source":"system","sensitive":true}'

# Expected response format:
# {
#   "key": "displayName",
#   "value": "Mark", 
#   "updated_at": "2024-01-01 12:00:00"
# }
```

## Get KV Pairs
```bash
# Get displayName (should preserve exact casing)
curl -X GET http://localhost:8000/kv/displayName

# Get favorite color
curl -X GET http://localhost:8000/kv/favorite_color

# Get sensitive data (redacted unless DEBUG=true)
curl -X GET http://localhost:8000/kv/api_key

# Expected response format:
# {
#   "key": "displayName",
#   "value": "Mark",
#   "updated_at": "2024-01-01 12:00:00",
#   "source": "user",
#   "sensitive": false
# }

# 404 for non-existent key
curl -X GET http://localhost:8000/kv/nonexistent
```

## List All KV Pairs
```bash
curl -X GET http://localhost:8000/kv/list

# Expected response format:
# {
#   "items": [
#     {
#       "key": "displayName",
#       "value": "Mark",
#       "updated_at": "2024-01-01 12:00:00",
#       "sensitive": false
#     },
#     {
#       "key": "favorite_color", 
#       "value": "Purple",
#       "updated_at": "2024-01-01 12:01:00",
#       "sensitive": false
#     }
#   ],
#   "count": 2
# }
```

## Add Episodic Events
```bash
# Add a custom episodic event
curl -X POST http://localhost:8000/episodic \
  -H "Content-Type: application/json" \
  -d '{
    "actor": "test_user",
    "action": "manual_test",
    "payload": {"test": "data", "timestamp": "2024-01-01"}
  }'

# Expected response format:
# {
#   "id": 1,
#   "ts": "2024-01-01 12:00:00"
# }
```

## Debug Information (DEBUG mode only)
```bash
# Get recent episodic events (only works if DEBUG=true in .env)
curl -X GET http://localhost:8000/debug

# Expected response format:
# {
#   "recent_events": [
#     {
#       "id": 1,
#       "ts": "2024-01-01 12:00:00",
#       "actor": "memory_manager", 
#       "action": "kv_set",
#       "payload": "{\"key\": \"displayName\", \"value\": \"Mark\", \"source\": \"user\"}"
#     }
#   ],
#   "debug_enabled": true
# }

# If DEBUG=false, returns 403 Forbidden
```

## Error Cases
```bash
# Invalid source (should return 400)
curl -X PUT http://localhost:8000/kv \
  -H "Content-Type: application/json" \
  -d '{"key":"test","value":"value","source":"invalid"}'

# Missing required field (should return 422)
curl -X PUT http://localhost:8000/kv \
  -H "Content-Type: application/json" \
  -d '{"key":"test"}'

# Non-existent key (should return 404)
curl -X GET http://localhost:8000/kv/does_not_exist
```

## One-Liner Smoke Test Sequence
```bash
# Complete smoke test in one command block
curl -X PUT http://localhost:8000/kv -H "Content-Type: application/json" -d '{"key":"displayName","value":"Mark","source":"user"}' && \
curl -X GET http://localhost:8000/kv/displayName && \
curl -X GET http://localhost:8000/kv/list && \
curl -X GET http://localhost:8000/health && \
echo "✅ Smoke test complete"
```

## Expected Behavior Verification

### Casing Preservation
```bash
# Set with exact casing
curl -X PUT http://localhost:8000/kv -H "Content-Type: application/json" -d '{"key":"displayName","value":"Mark Snow","source":"user"}'

# Get back - should preserve "displayName" and "Mark Snow" exactly
curl -X GET http://localhost:8000/kv/displayName
```

### Timestamp Updates
```bash
# Set initial value
curl -X PUT http://localhost:8000/kv -H "Content-Type: application/json" -d '{"key":"test_time","value":"first","source":"test"}'

# Wait a moment, then update
sleep 1
curl -X PUT http://localhost:8000/kv -H "Content-Type: application/json" -d '{"key":"test_time","value":"second","source":"test"}'

# Check that updated_at timestamp increased
curl -X GET http://localhost:8000/kv/test_time
```

### Sensitive Data Redaction
```bash
# Ensure DEBUG=false in .env, restart server
# Set sensitive data
curl -X PUT http://localhost:8000/kv -H "Content-Type: application/json" -d '{"key":"secret","value":"sensitive_data","sensitive":true}'

# Should return "***REDACTED***" as value
curl -X GET http://localhost:8000/kv/secret

# Change DEBUG=true, restart server
# Should return actual value
curl -X GET http://localhost:8000/kv/secret
```

## Next Steps

After verifying all curl examples work:
1. Run automated tests: `make smoke`
2. Complete Stage 1 checklist in `docs/STAGE_CHECKS.md`
3. Get human approval before Stage 2 development