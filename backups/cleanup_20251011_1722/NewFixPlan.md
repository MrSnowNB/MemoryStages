# NewFixPlan.md - Complete Stage 1 Memory System Implementation

## 🎯 **PURPOSE**
Implement a clean, deterministic memory system with proper short-circuiting, validation semantics, and comprehensive testing.

## 📋 **EXECUTION ORDER**

### **Part 0 — Environment Setup**
- ✅ **Terminal**: `cd /path/to/MemoryStages`
- ✅ **Env**: `cp .env.example .env`
- ✅ **Deps**: `pip install -r requirements.txt`
- ✅ **Server**: `make dev` (FastAPI at http://localhost:8000)
- ✅ **Web UI**: Serve `web/index.html` at http://localhost:3000
- ✅ **Ollama**: `ollama list`, verify model available

### **Part 1 — Config Validation**
- ✅ **File**: `src/core/config.py`
- ✅ **Verify**:
  - `CHAT_API_ENABLED = True`
  - `SWARM_ENABLED = True`
  - `OLLAMA_MODEL` matches local model
  - `OLLAMA_HOST = "http://localhost:11434"`

### **Part 2 — Chat API Deterministic KV Path**
**File**: `src/api/chat.py`

#### **Step 2.1: Add Imports & Helpers**
```python
import re
from typing import Optional, Dict, Any, List

KEY_ALIASES = {
    "display name": "displayName",
    "name": "displayName",
    "nickname": "displayName",
    "user name": "displayName",
}

def _normalize_key(raw: str) -> str:
    k = (raw or "").strip().lower()
    if k in KEY_ALIASES:
        return KEY_ALIASES[k]
    parts = [p for p in re.split(r"\s+", k) if p]
    if not parts:
        return k
    return parts[0] + "".join(p.capitalize() for p in parts[1:])

def _parse_memory_write_intent(text: str) -> Optional[Dict[str, str]]:
    if not text:
        return None
    t = text.strip()
    patterns = [
        r"^\s*set\s+my\s+(.+?)\s+to\s+(.+)$",
        r"^\s*remember\s+my\s+(.+?)\s+is\s+(.+)$",
        r"^\s*remember\s+that\s+my\s+(.+?)\s+is\s+(.+)$",
        r"^\s*my\s+(.+?)\s+is\s+(.+?)\s*(?:,?\s*remember\s+that)?$",
    ]
    for pat in patterns:
        m = re.match(pat, t, flags=re.IGNORECASE)
        if m:
            raw_key = m.group(1).strip().strip(":")
            value = m.group(2).strip().strip(".").strip("'").strip('"')
            # remove trailing "remember it/that"
            value = re.sub(r"\s*,?\s*remember\s+(it|that)\s*$", "", value, flags=re.I).strip()
            key = _normalize_key(raw_key)
            if key and value:
                return {"key": key, "value": value}
    return None

def _parse_memory_read_intent(text: str) -> Optional[str]:
    if not text:
        return None
    t = text.strip()
    # what is my <key> / what is my display name / what's my display name
    m = re.match(r"^\s*what(?:'s| is)\s+my\s+(.+?)\s*\??$", t, flags=re.IGNORECASE)
    if m:
        return _normalize_key(m.group(1))
    return None
```

#### **Step 2.2: Implement Deterministic Chat Handler**
```python
@router.post("/chat/message", response_model=ChatResponse)
async def send_chat_message(
    req: ChatRequest,
    authorization: Optional[str] = Header(None),
    dao: DAO = Depends(DAO.dep),
    orch: Orchestrator = Depends(Orchestrator.dep),
):
    # Optional dev auth: accept "Bearer web-demo-token"
    # if authorization_required and invalid -> raise HTTPException(401)

    memory_sources: List[str] = []

    # 1) Memory WRITE intent
    try:
        write_intent = _parse_memory_write_intent(req.content or "")
    except Exception:
        write_intent = None
    if write_intent:
        # Validate key before writing
        key = write_intent["key"]
        value = write_intent["value"]
        # Enforce safe key pattern (letters, digits, underscores; allow camelCase)
        if not re.match(r"^[A-Za-z][A-Za-z0-9_]*$", key):
            raise HTTPException(status_code=400, detail=f"Invalid key: {key}")
        await dao.set_key(
            key=key,
            value=value,
            source="chat_api",
            casing="preserve",
            sensitive=False,
        )
        await dao.add_event(event_type="kv_write", payload={"key": key, "source": "chat_api"})
        memory_sources.append(f"kv:{key}")
        return ChatResponse(
            content=f"Stored {key} = '{value}' in canonical memory.",
            confidence=1.0,
            validation_passed=True,
            agents_consulted=0,
            memory_sources=memory_sources,
            debug={"path": "write_intent"},
        )

    # 2) Memory READ intent (deterministic, no agents)
    try:
        read_key = _parse_memory_read_intent(req.content or "")
    except Exception:
        read_key = None
    if read_key:
        rec = await dao.get_key(read_key)
        if rec and rec.value:
            memory_sources.append(f"kv:{read_key}")
            await dao.add_event(event_type="kv_read", payload={"key": read_key})
            return ChatResponse(
                content=f"Your {read_key} is '{rec.value}'.",
                confidence=1.0,
                validation_passed=True,
                agents_consulted=0,
                memory_sources=memory_sources,
                debug={"path": "read_intent"},
            )
        # if no KV, fall through to orchestrator

    # 3) General query → orchestrator
    result = await orch.process_user_message(req.content or "", req.session_id, dao=dao)
    return ChatResponse(**result)
```

### **Part 3 — Validation Semantics & Provenance**
**File**: `src/agents/memory_adapter.py`

#### **Step 3.1: Validation Response**
```python
def validate_facts_in_response(self, response: str, context: Dict[str, Any]) -> Dict[str, Any]:
    kv = context.get("kv", [])
    score = self._keyword_overlap(response, kv)
    kv_keys = [k.get("key") for k in kv if k.get("key")]
    kv_sources = [f"kv:{k}" for k in kv_keys]
    return {
        "score": score,
        "kv_keys": kv_keys,
        "kv_sources": kv_sources,
    }
```

#### **Step 3.2: Validation Context**
```python
async def get_validation_context(self, query: str, dao: DAO) -> Dict[str, Any]:
    ctx = {"kv": [], "episodic": [], "faiss": []}
    try:
        if re.search(r"\b(display\s*name|displayName|name|nickname|user\s*name)\b", query or "", re.I):
            rec = await dao.get_key("displayName")
            if rec and not rec.sensitive:
                ctx["kv"].append({"key": rec.key, "value": rec.value})
    except Exception:
        pass
    if not ctx["kv"]:
        # fallback: include some recent non-sensitive keys
        items = await dao.list_keys()
        for r in items[:20]:
            if not getattr(r, "sensitive", False):
                ctx["kv"].append({"key": r.key, "value": r.value})
    return ctx
```

**File**: `src/agents/orchestrator.py`

#### **Step 3.3: Final Response Assembly**
```python
def _finalize(self, agent_outputs, validation):
    score = validation.get("score", 0.0)
    kv_sources = validation.get("kv_sources", [])
    validation_passed = bool(kv_sources) and score >= 0.5
    return {
        "content": validation.get("selected_response", agent_outputs[0]["content"] if agent_outputs else ""),
        "confidence": validation.get("confidence", score),
        "validation_passed": validation_passed,
        "agents_consulted": len(agent_outputs),
        "memory_sources": kv_sources or [],
        "debug": {"validation": validation, "agents": [a.get("meta") for a in agent_outputs]},
    }
```

### **Part 4 — KV API Improvements**
**File**: `src/api/main.py`

#### **Step 4.1: KV List Endpoint**
```python
@router.get("/kv/list", response_model=KVListResponse)
async def list_keys_endpoint(dao: DAO = Depends(DAO.dep)):
    items = await dao.list_keys()
    return KVListResponse(
        items=[
            KVGetResponse(
                key=i.key,
                value=i.value,
                casing=getattr(i, "casing", "preserve"),
                source=getattr(i, "source", "unknown"),
                updated_at=i.updated_at,
                sensitive=bool(getattr(i, "sensitive", False)),
            )
            for i in items
        ]
    )
```

#### **Step 4.2: KV Put Endpoint with Validation**
```python
@router.put("/kv", response_model=KVGetResponse)
async def put_kv(req: KVPutRequest, dao: DAO = Depends(DAO.dep)):
    if not re.match(r"^[A-Za-z][A-Za-z0-9_]*$", req.key):
        raise HTTPException(status_code=400, detail=f"Invalid key: {req.key}")
    await dao.set_key(
        key=req.key,
        value=req.value,
        source=req.source or "api",
        casing=req.casing or "preserve",
        sensitive=bool(req.sensitive),
    )
    rec = await dao.get_key(req.key)
    return KVGetResponse(
        key=rec.key, value=rec.value, casing=rec.casing, source=rec.source,
        updated_at=rec.updated_at, sensitive=rec.sensitive
    )
```

#### **Step 4.3: Cleanup Script** (`scripts/cleanup_kv.py`)
```python
import asyncio
import re
from src.core.dao import DAO

INVALID_KEYS = {"", "what"}
DUPLICATES = {"displayname"}  # duplicated variant of displayName
PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")

async def main():
    dao = DAO()
    items = await dao.list_keys()
    for i in items:
        if i.key in INVALID_KEYS or i.key in DUPLICATES or not PATTERN.match(i.key):
            print("Deleting:", i.key)
            await dao.delete_key(i.key)

if __name__ == "__main__":
    asyncio.run(main())
```

### **Part 5 — Web UI Truth-in-Telemetry**
**File**: `web/index.html`

```javascript
function renderStatus(meta) {
  const agents = meta.agents_consulted ?? 0;
  const validated = meta.validation_passed === true;
  const sources = meta.memory_sources || [];
  statusEl.textContent = `Agents: ${agents} | Validation: ${validated ? 'KV ✓' : '—'}`;
  if (agents === 0 && validated && sources.length > 0) {
    provenanceEl.textContent = `Source: ${sources.join(', ')}`;
  } else {
    provenanceEl.textContent = '';
  }
}
```

### **Part 6 — Comprehensive Tests**
**File**: `tests/test_chat_memory.py`

```python
import pytest
from httpx import AsyncClient
from src.api.main import app

@pytest.mark.asyncio
async def test_kv_persistence_roundtrip():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.put("/kv", json={"key":"displayName","value":"Mark","source":"test","casing":"preserve","sensitive":False})
        assert r.status_code == 200
        r = await ac.get("/kv/displayName")
        assert r.status_code == 200 and r.json()["value"] == "Mark"
        r = await ac.get("/kv/list")
        assert r.status_code == 200
        keys = [i["key"] for i in r.json()["items"]]
        assert "displayName" in keys

@pytest.mark.asyncio
async def test_chat_sets_memory_on_intent():
    headers = {"Authorization":"Bearer web-demo-token"}
    async with AsyncClient(app=app, base_url="http://test", headers=headers) as ac:
        r = await ac.post("/chat/message", json={"content":"Set my displayName to Mark"})
        assert r.status_code == 200
        data = r.json()
        assert data["agents_consulted"] == 0
        assert data["validation_passed"] is True
        assert "kv:displayName" in data["memory_sources"]
        r = await ac.get("/kv/displayName")
        assert r.json()["value"] == "Mark"

@pytest.mark.asyncio
async def test_chat_reads_memory_short_circuit():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        await ac.put("/kv", json={"key":"displayName","value":"Mark","source":"test","casing":"preserve","sensitive":False})
    headers = {"Authorization":"Bearer web-demo-token"}
    async with AsyncClient(app=app, base_url="http://test", headers=headers) as ac:
        for prompt in ["What is my displayName?", "what is my display name?", "what's my display name?"]:
            r = await ac.post("/chat/message", json={"content":prompt})
            assert r.status_code == 200
            data = r.json()
            assert "Mark" in data["content"]
            assert data["agents_consulted"] == 0
            assert data["validation_passed"] is True
            assert "kv:displayName" in data["memory_sources"]

@pytest.mark.asyncio
async def test_swarm_activation_for_general_query():
    headers = {"Authorization":"Bearer web-demo-token"}
    async with AsyncClient(app=app, base_url="http://test", headers=headers) as ac:
        r = await ac.post("/chat/message", json={"content":"Explain gradient descent in simple terms."})
        assert r.status_code == 200
        data = r.json()
        assert data["agents_consulted"] >= 1
        # validation may be false if no KV support
```

### **Part 7 — Manual Validation Steps**
1. **Restart API**: `make dev`
2. **Web UI Tests**:
   - "Set my displayName to Mark" → agents=0, validation=true, "Source: kv:displayName"
   - "What is my displayName?" → agents=0, validation=true, shows stored value
   - "Explain gradient descent" → agents>0, validation=false (unless KV context exists)
3. **API Tests**:
   - `GET /kv/list` → shows clean keys only
   - `PUT /kv` with invalid key → 400 error

### **Part 8 — Optional Debug Endpoint**
```python
@router.get("/debug/status")
async def debug_status(dao: DAO = Depends(DAO.dep), orch: Orchestrator = Depends(Orchestrator.dep)):
    return {
        "CHAT_API_ENABLED": True,
        "SWARM_ENABLED": True,
        "agents_count": len(orch.agents),
        "agents": getattr(orch, "agents_meta", []),
        "kv_count": len(await dao.list_keys()),
    }
```

## 🎯 **EXPECTED FINAL BEHAVIOR**

### **Memory Path (agents=0)**
- "What is my displayName?" → `agents_consulted=0`, exact KV value, validation badge ✅

### **Swarm Path (agents>0)**
- "Explain gradient descent" → `agents_consulted=4+`, swarm reasoning, validation based on KV correlation

### **Data Integrity**
- Clean KV store with validated keys only
- User isolation preserved
- Audit trails for all operations

## 📊 **SUCCESS CRITERIA**

- ✅ **Deterministic Paths**: Memory questions bypass agents entirely
- ✅ **Smart Validation**: Only KV-backed responses show validation badge
- ✅ **Clean Persistence**: No malformed keys, proper key validation
- ✅ **Comprehensive Tests**: All key behaviors have regression tests
- ✅ **Transparent UI**: Accurate telemetry and status indicators

**This implementation provides the clean, testable Stage 1 foundation with proper dual-path architecture.**
