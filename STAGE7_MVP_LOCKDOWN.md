# STAGE 7 MVP LOCKDOWN: Rule-Based Orchestrator Swarm Chatbot

**⚠️ STAGE 7 MVP SCOPE ONLY - RAPID DELIVERY FOCUSED ⚠️**

## Prerequisites

- Stage 1-6 **COMPLETE** and **HUMAN-APPROVED**
- All Stage 1-6 tests pass with all feature combinations
- Python 3.10+ environment
- Ollama installed and running locally with liquid-rag:latest model
- **TARGET: MVP chatbot ready for demo/frontend tonight**

## Stage 7 MVP Objectives (LOCKED SCOPE)

Implement **production-ready rule-based orchestrator managing Ollama bot swarm** for immediate MVP delivery:

✅ **IN SCOPE (MVP FOCUSED)**:
- Rule-based Python orchestrator managing 4+ tiny Ollama agents
- Single global `OLLAMA_MODEL` variable for instant system-wide model swapping
- Strict memory validation - all responses must be traceable to canonical memory
- Privacy-enforced memory adapter preventing any data leakage
- Feature-flagged /chat API endpoints ready for frontend integration
- Session management with secure logging and admin review
- Complete response validation - no hallucinations allowed

🚫 **OUT OF SCOPE (POST-MVP)**:
- Complex multi-agent communication protocols
- LLM-based orchestrator (rule-based for speed)
- Advanced plugin ecosystem (optional math plugin only)
- Real-time learning or model fine-tuning
- Complex authentication beyond admin tokens
- Multi-tenant or enterprise features

## Critical Constraints (MVP SAFETY REQUIREMENTS)

### Architecture Constraints
- **Rule-based orchestrator only** - no LLM orchestration for MVP speed
- **Single global OLLAMA_MODEL** controls all agents - zero code changes for swaps
- **Memory adapter gatekeeper** - no direct database/file access by agents
- **Response validation mandatory** - all outputs validated against canonical memory
- **Privacy-first design** - sensitive data never reaches agents

### Implementation Constraints
- **Slice-by-slice delivery** - each slice fully tested before next
- **Comprehensive logging** - every message, agent output, validation logged
- **MVP-ready testing** - manual runbook and automated tests per slice
- **Rollback capability** - each slice can be reverted if gates fail
- **Tonight delivery** - optimized for rapid but safe implementation

## Environment and Configuration

### Single-Point Model Control
```bash
# SINGLE VARIABLE CONTROLS ENTIRE SWARM
OLLAMA_MODEL=liquid-rag:latest       # Default production model
# OLLAMA_MODEL=gemma:2b              # Fast alternative
# OLLAMA_MODEL=llama3.2:1b           # Lightweight option
# OLLAMA_MODEL=qwen2:0.5b            # Ultra-lightweight

# MVP Configuration
SWARM_ENABLED=false                  # Master switch (default: OFF)
SWARM_AGENT_COUNT=4                  # Number of agents in swarm
SWARM_ORCHESTRATOR_TYPE=rule_based   # rule_based|llm_based (rule_based for MVP)
CHAT_API_ENABLED=false               # Chat endpoints (default: OFF)
RESPONSE_VALIDATION_STRICT=true      # Strict memory validation
```

### MVP Agent Swarm Architecture
```
┌─────────────────────────────────────────────────┐
│               Rule-Based Orchestrator            │
│  ┌─────────────────────────────────────────────┐ │
│  │ • Collects responses from 4+ agents        │ │
│  │ • Validates against canonical memory       │ │
│  │ • Selects/combines best validated response │ │
│  │ • Logs every decision and validation       │ │
│  └─────────────────────────────────────────────┘ │
└─────────────────┬───────────────────────────────┘
                  │
        ┌─────────┴─────────┐
        │  Memory Adapter   │ ← Privacy Gatekeeper
        │  (Privacy Guard)  │
        └─────────┬─────────┘
                  │
    ┌─────────────┼─────────────┐
    ▼             ▼             ▼
┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐
│Agent 1  │  │Agent 2  │  │Agent 3  │  │Agent 4+ │
│Ollama   │  │Ollama   │  │Ollama   │  │Ollama   │
│Bot      │  │Bot      │  │Bot      │  │Bot      │
└─────────┘  └─────────┘  └─────────┘  └─────────┘
     │             │             │             │
     └─────────────┴─────────────┴─────────────┘
              All use OLLAMA_MODEL
```

## File Touch Policy (STRICT MVP)

### Allowed Files for Stage 7 MVP ONLY
```
# Core Orchestrator and Swarm
src/agents/orchestrator.py           (create - rule-based orchestrator)
src/agents/agent.py                  (create - base agent interface)
src/agents/ollama_agent.py           (create - Ollama agent implementation)
src/agents/registry.py               (create - agent swarm registry)
src/agents/memory_adapter.py         (create - privacy-enforced memory access)

# Chat API
src/api/chat.py                      (create - MVP chat endpoints)
src/api/schemas.py                   (modify - add chat schemas)

# Session and Config
src/core/session.py                  (create - session management)
src/core/config.py                   (modify - add OLLAMA_MODEL global)

# Testing (MVP Critical)
tests/test_orchestrator.py           (create - orchestrator tests)
tests/test_memory_adapter.py         (create - memory/privacy tests)
tests/test_chat_api.py               (create - API integration tests)
tests/test_agent_registry.py         (create - swarm tests)
tests/test_session.py                (create - session tests)

# Optional Plugin (Time Permitting)
src/agents/plugins.py                (create - simple math plugin)
tests/test_agent_plugins.py          (create - plugin tests)

# Documentation (MVP Essentials)
docs/FRONTEND_API_CONTRACT.md        (create - API contract for frontend)
docs/MODEL_SWAPPING.md               (create - single-variable swap guide)
examples/chat_demo.py                (create - MVP demo script)

# Build System
Makefile                            (modify - add Stage 7 MVP targets)
requirements.txt                    (modify - add Ollama dependencies)
```

## Stage 7 MVP Implementation Slices

### Slice 7.1: Orchestrator & Swarm Bootstrapping

**Purpose**: Create rule-based orchestrator managing 4+ Ollama agents with single-point model control.

**Allowed Files**:
- `src/core/config.py` (modify - add OLLAMA_MODEL global)
- `src/agents/orchestrator.py` (create)
- `src/agents/agent.py` (create)
- `src/agents/ollama_agent.py` (create)
- `src/agents/registry.py` (create)
- `tests/test_orchestrator.py` (create)
- `tests/test_agent_registry.py` (create)

**MVP Deliverables**:

**Global Configuration** (`src/core/config.py` addition):
```python
# MVP Swarm Configuration - SINGLE POINT OF CONTROL
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "liquid-rag:latest")
SWARM_AGENT_COUNT = int(os.getenv("SWARM_AGENT_COUNT", "4"))
SWARM_ORCHESTRATOR_TYPE = os.getenv("SWARM_ORCHESTRATOR_TYPE", "rule_based")
RESPONSE_VALIDATION_STRICT = os.getenv("RESPONSE_VALIDATION_STRICT", "true").lower() == "true"
```

**Rule-Based Orchestrator** (`src/agents/orchestrator.py`):
```python
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from .agent import AgentMessage, AgentResponse
from .registry import AgentRegistry
from .memory_adapter import MemoryAdapter
from ..core.config import config
from ..core import dao

@dataclass
class OrchestratorDecision:
    selected_response: str
    confidence: float
    agents_consulted: List[str]
    validation_passed: bool
    memory_sources: List[str]
    decision_reasoning: str

class RuleBasedOrchestrator:
    """
    Rule-based orchestrator managing Ollama agent swarm.
    Validates all responses against canonical memory before user delivery.
    """
    
    def __init__(self):
        self.agent_registry = AgentRegistry()
        self.memory_adapter = MemoryAdapter()
        self.decision_log = []
        
        # Initialize agent swarm using OLLAMA_MODEL
        self.agents = self._initialize_swarm()
        
    def _initialize_swarm(self) -> List[str]:
        """Initialize swarm of Ollama agents using global model."""
        agents = []
        for i in range(config.SWARM_AGENT_COUNT):
            agent_id = f"ollama_agent_{i+1}"
            agent = self.agent_registry.create_ollama_agent(
                agent_id=agent_id,
                model_name=config.OLLAMA_MODEL,
                role_context=f"Agent {i+1} in swarm"
            )
            agents.append(agent_id)
            
        # Log swarm initialization
        dao.add_event(
            actor="orchestrator",
            action="swarm_initialized",
            payload={
                "agent_count": len(agents),
                "model": config.OLLAMA_MODEL,
                "agents": agents
            }
        )
        
        return agents
    
    def process_user_message(self, message: str, session_id: str, user_id: str = None) -> AgentResponse:
        """
        Process user message through agent swarm with strict validation.
        All responses must be validated against canonical memory.
        """
        start_time = datetime.now()
        
        try:
            # Get memory context for validation
            memory_context = self.memory_adapter.get_validation_context(
                query=message,
                user_id=user_id
            )
            
            # Collect responses from swarm
            agent_responses = self._collect_swarm_responses(message, session_id)
            
            # Apply rule-based decision logic
            decision = self._make_orchestrator_decision(
                user_message=message,
                agent_responses=agent_responses,
                memory_context=memory_context
            )
            
            # Validate final response against memory
            validated_response = self._validate_response_against_memory(
                response=decision.selected_response,
                memory_context=memory_context,
                user_query=message
            )
            
            # Create final response
            final_response = AgentResponse(
                content=validated_response,
                model_used=config.OLLAMA_MODEL,
                confidence=decision.confidence,
                tool_calls=[],
                processing_time_ms=int((datetime.now() - start_time).total_seconds() * 1000),
                metadata={
                    "orchestrator_type": "rule_based",
                    "agents_consulted": decision.agents_consulted,
                    "validation_passed": decision.validation_passed,
                    "memory_sources": decision.memory_sources
                },
                audit_info={
                    "session_id": session_id,
                    "user_id": user_id,
                    "decision_reasoning": decision.decision_reasoning,
                    "swarm_size": len(agent_responses)
                }
            )
            
            # Log orchestrator decision
            self._log_orchestrator_decision(decision, final_response, message)
            
            return final_response
            
        except Exception as e:
            # Error handling with fallback
            error_response = AgentResponse(
                content="I apologize, but I encountered an error processing your request. Please try rephrasing your question.",
                model_used=config.OLLAMA_MODEL,
                confidence=0.0,
                tool_calls=[],
                processing_time_ms=int((datetime.now() - start_time).total_seconds() * 1000),
                metadata={"error": str(e)},
                audit_info={"orchestrator_error": str(e)}
            )
            
            # Log error
            dao.add_event(
                actor="orchestrator_error",
                action="processing_failed",
                payload={
                    "error": str(e),
                    "session_id": session_id,
                    "model": config.OLLAMA_MODEL
                }
            )
            
            return error_response
    
    def _collect_swarm_responses(self, message: str, session_id: str) -> List[AgentResponse]:
        """Collect responses from all agents in swarm."""
        responses = []
        
        agent_message = AgentMessage(
            content=message,
            role="user",
            timestamp=datetime.now(),
            metadata={"session_id": session_id},
            model_used=""
        )
        
        for agent_id in self.agents:
            try:
                agent = self.agent_registry.get_agent(agent_id)
                response = agent.process_message(agent_message, [])
                responses.append(response)
            except Exception as e:
                # Log agent failure but continue with other agents
                dao.add_event(
                    actor=f"agent_error_{agent_id}",
                    action="agent_failed",
                    payload={"error": str(e)}
                )
        
        return responses
    
    def _make_orchestrator_decision(self, user_message: str, 
                                  agent_responses: List[AgentResponse],
                                  memory_context: List[Dict[str, Any]]) -> OrchestratorDecision:
        """
        Rule-based decision making for response selection.
        Prioritizes responses that can be validated against memory.
        """
        if not agent_responses:
            return OrchestratorDecision(
                selected_response="I don't have enough information to answer that question.",
                confidence=0.1,
                agents_consulted=[],
                validation_passed=False,
                memory_sources=[],
                decision_reasoning="No agent responses available"
            )
        
        best_response = None
        best_score = 0.0
        reasoning_parts = []
        
        for response in agent_responses:
            score = 0.0
            
            # Rule 1: Prefer responses that reference memory context
            if self._response_references_memory(response.content, memory_context):
                score += 0.4
                reasoning_parts.append("references_memory")
            
            # Rule 2: Prefer confident responses
            score += response.confidence * 0.3
            
            # Rule 3: Prefer responses with reasonable length (not too short/long)
            content_length = len(response.content)
            if 20 <= content_length <= 500:
                score += 0.2
            
            # Rule 4: Avoid responses that seem like hallucinations
            if not self._detect_potential_hallucination(response.content, memory_context):
                score += 0.1
            else:
                reasoning_parts.append("potential_hallucination_detected")
            
            if score > best_score:
                best_score = score
                best_response = response
        
        if best_response:
            return OrchestratorDecision(
                selected_response=best_response.content,
                confidence=best_score,
                agents_consulted=[f"agent_{i+1}" for i in range(len(agent_responses))],
                validation_passed=best_score > 0.3,
                memory_sources=[ctx.get("source", "unknown") for ctx in memory_context],
                decision_reasoning="; ".join(reasoning_parts) if reasoning_parts else "default_selection"
            )
        else:
            return OrchestratorDecision(
                selected_response="I need more specific information to help you with that.",
                confidence=0.1,
                agents_consulted=[],
                validation_passed=False,
                memory_sources=[],
                decision_reasoning="no_suitable_response_found"
            )
    
    def _validate_response_against_memory(self, response: str, 
                                        memory_context: List[Dict[str, Any]],
                                        user_query: str) -> str:
        """
        Validate response against canonical memory.
        Returns validated response or requests clarification.
        """
        if not config.RESPONSE_VALIDATION_STRICT:
            return response
        
        # If response references facts, validate against memory
        if memory_context and self._response_makes_factual_claims(response):
            validated_facts = self.memory_adapter.validate_facts_in_response(
                response=response,
                memory_context=memory_context
            )
            
            if not validated_facts:
                return "I don't have verified information about that topic. Could you please provide more specific details or rephrase your question?"
        
        # Check for potential sensitive data leakage
        if self.memory_adapter.contains_sensitive_data(response):
            return "I can't provide that information due to privacy restrictions. Please ask about non-sensitive topics."
        
        return response
    
    def _response_references_memory(self, response: str, memory_context: List[Dict[str, Any]]) -> bool:
        """Check if response references information from memory context."""
        if not memory_context:
            return False
        
        response_lower = response.lower()
        for ctx in memory_context:
            content = ctx.get("content", "").lower()
            if content and len(content) > 10:
                # Simple keyword overlap check
                content_words = set(content.split())
                response_words = set(response_lower.split())
                overlap = len(content_words & response_words)
                if overlap >= min(3, len(content_words) // 2):
                    return True
        return False
    
    def _detect_potential_hallucination(self, response: str, memory_context: List[Dict[str, Any]]) -> bool:
        """Detect responses that might be hallucinations."""
        # Simple heuristics for hallucination detection
        hallucination_indicators = [
            "according to my knowledge",
            "i remember that",
            "in my experience",
            "i believe that",
            "it's commonly known that"
        ]
        
        response_lower = response.lower()
        for indicator in hallucination_indicators:
            if indicator in response_lower:
                return True
        
        return False
    
    def _response_makes_factual_claims(self, response: str) -> bool:
        """Check if response makes factual claims that should be validated."""
        factual_indicators = [
            "is", "are", "was", "were", "has", "have", "will",
            "according to", "the fact is", "actually", "specifically"
        ]
        
        response_lower = response.lower()
        return any(indicator in response_lower for indicator in factual_indicators)
    
    def _log_orchestrator_decision(self, decision: OrchestratorDecision, 
                                 final_response: AgentResponse, user_message: str):
        """Log orchestrator decision for audit and debugging."""
        dao.add_event(
            actor="orchestrator",
            action="decision_made",
            payload={
                "user_message_length": len(user_message),
                "selected_response_length": len(decision.selected_response),
                "confidence": decision.confidence,
                "agents_consulted": decision.agents_consulted,
                "validation_passed": decision.validation_passed,
                "memory_sources_count": len(decision.memory_sources),
                "decision_reasoning": decision.decision_reasoning,
                "model": config.OLLAMA_MODEL,
                "processing_time_ms": final_response.processing_time_ms
            }
        )
```

**Test Plan**:
```bash
# Test orchestrator with swarm
SWARM_ENABLED=true OLLAMA_MODEL=liquid-rag:latest pytest tests/test_orchestrator.py -v

# Test agent registry
pytest tests/test_agent_registry.py -v
```

**MVP Gate Criteria**:
- [ ] All orchestration and agent registry tests pass
- [ ] Orchestrator logs every decision with reasoning
- [ ] Swarm of 4+ agents initialized with OLLAMA_MODEL
- [ ] Rule-based decision making functional
- [ ] Memory validation integrated into decision flow

**Rollback Plan**: Delete src/agents/ directory, revert config.py

---

### Slice 7.2: Memory Adapter & Response Validation

**Purpose**: Create privacy-enforcing memory adapter and strict response validation against canonical memory.

**Allowed Files**:
- `src/agents/memory_adapter.py` (create)
- `tests/test_memory_adapter.py` (create)

**MVP Deliverables**:

**Memory Adapter** (`src/agents/memory_adapter.py`):
```python
from typing import List, Dict, Any, Optional
from datetime import datetime
from ..core import dao
from ..core.config import config
import re

class MemoryAdapter:
    """
    Privacy-enforcing gateway between agents and canonical memory.
    NO agent can bypass this adapter to access memory directly.
    """
    
    def __init__(self):
        self.access_log = []
        self.validation_cache = {}
        
    def get_validation_context(self, query: str, user_id: str = None, 
                             max_results: int = 3) -> List[Dict[str, Any]]:
        """
        Get memory context for response validation.
        Applies strict privacy and tombstone filtering.
        """
        try:
            # Log memory access attempt
            self._log_memory_access("validation_context", query, user_id)
            
            # Use existing Stage 2 vector search if available
            context_results = []
            
            if hasattr(config, 'VECTOR_ENABLED') and config.VECTOR_ENABLED:
                try:
                    from ..core.search_service import semantic_search
                    search_results = semantic_search(query=query, top_k=max_results)
                    
                    for result in search_results:
                        # Apply strict privacy filtering
                        if self._is_safe_for_context(result):
                            context_results.append({
                                'content': result.get('value', ''),
                                'source': result.get('source', 'memory'),
                                'updated_at': result.get('updated_at'),
                                'key': result.get('key', ''),
                                'sensitive': result.get('sensitive', False)
                            })
                except ImportError:
                    # Fallback to basic KV search
                    context_results = self._fallback_context_search(query, max_results)
            else:
                context_results = self._fallback_context_search(query, max_results)
            
            # Log successful context retrieval
            self._log_memory_access("context_retrieved", query, user_id, 
                                  results_count=len(context_results))
            
            return context_results
            
        except Exception as e:
            # Log error and return empty context
            self._log_memory_access("context_error", query, user_id, error=str(e))
            return []
    
    def validate_facts_in_response(self, response: str, 
                                 memory_context: List[Dict[str, Any]]) -> bool:
        """
        Validate that factual claims in response are supported by memory.
        Returns True if facts are validated, False if suspicious.
        """
        if not memory_context:
            return False
        
        # Extract potential facts from response
        response_facts = self._extract_facts_from_response(response)
        
        if not response_facts:
            return True  # No factual claims to validate
        
        # Check facts against memory context
        validated_count = 0
        for fact in response_facts:
            if self._fact_supported_by_memory(fact, memory_context):
                validated_count += 1
        
        # Require at least 70% of facts to be validated
        validation_threshold = 0.7
        validation_ratio = validated_count / len(response_facts) if response_facts else 1.0
        
        is_validated = validation_ratio >= validation_threshold
        
        # Log validation attempt
        dao.add_event(
            actor="memory_adapter",
            action="fact_validation",
            payload={
                "response_length": len(response),
                "facts_found": len(response_facts),
                "facts_validated": validated_count,
                "validation_ratio": validation_ratio,
                "validation_passed": is_validated
            }
        )
        
        return is_validated
    
    def contains_sensitive_data(self, text: str) -> bool:
        """
        Check if text contains sensitive data patterns.
        Prevents sensitive data leakage in responses.
        """
        sensitive_patterns = [
            r'\b\d{3}-\d{2}-\d{4}\b',  # SSN
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email
            r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b',  # Credit card
            r'\b\d{10,}\b',  # Long numbers (could be sensitive IDs)
        ]
        
        for pattern in sensitive_patterns:
            if re.search(pattern, text):
                # Log sensitive data detection
                dao.add_event(
                    actor="memory_adapter",
                    action="sensitive_data_detected",
                    payload={
                        "pattern_type": "regex",
                        "text_length": len(text)
                    }
                )
                return True
        
        # Check for sensitive keywords
        sensitive_keywords = [
            'password', 'secret', 'private key', 'confidential',
            'ssn', 'social security', 'credit card', 'bank account'
        ]
        
        text_lower = text.lower()
        for keyword in sensitive_keywords:
            if keyword in text_lower:
                dao.add_event(
                    actor="memory_adapter",
                    action="sensitive_keyword_detected",
                    payload={
                        "keyword": keyword,
                        "text_length": len(text)
                    }
                )
                return True
        
        return False
    
    def _is_safe_for_context(self, memory_result: Dict[str, Any]) -> bool:
        """Check if memory result is safe to include in context."""
        # Skip sensitive data
        if memory_result.get('sensitive', False):
            return False
        
        # Skip tombstoned entries (empty values)
        if not memory_result.get('value', '').strip():
            return False
        
        # Skip if contains sensitive patterns
        content = memory_result.get('value', '')
        if self.contains_sensitive_data(content):
            return False
        
        return True
    
    def _fallback_context_search(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """Fallback context search using basic KV matching."""
        try:
            all_keys = dao.list_keys()
            relevant_context = []
            
            query_words = set(query.lower().split())
            
            for kv_item in all_keys[:50]:  # Limit search scope
                if not self._is_safe_for_context(kv_item):
                    continue
                
                # Simple keyword matching
                value_words = set(kv_item['value'].lower().split())
                overlap = len(query_words & value_words)
                
                if overlap > 0:
                    relevant_context.append({
                        'content': kv_item['value'],
                        'source': kv_item.get('source', 'memory'),
                        'updated_at': kv_item.get('updated_at'),
                        'key': kv_item['key'],
                        'relevance_score': overlap / len(query_words),
                        'sensitive': kv_item.get('sensitive', False)
                    })
            
            # Sort by relevance and return top results
            relevant_context.sort(key=lambda x: x['relevance_score'], reverse=True)
            return relevant_context[:max_results]
            
        except Exception as e:
            return []
    
    def _extract_facts_from_response(self, response: str) -> List[str]:
        """Extract potential factual statements from response."""
        # Simple sentence splitting and fact detection
        sentences = re.split(r'[.!?]+', response)
        facts = []
        
        fact_indicators = ['is', 'are', 'was', 'were', 'has', 'have', 'can', 'will']
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 10:  # Skip very short sentences
                words = sentence.lower().split()
                if any(indicator in words for indicator in fact_indicators):
                    facts.append(sentence)
        
        return facts
    
    def _fact_supported_by_memory(self, fact: str, memory_context: List[Dict[str, Any]]) -> bool:
        """Check if a fact is supported by memory context."""
        fact_words = set(fact.lower().split())
        
        for ctx in memory_context:
            content = ctx.get('content', '').lower()
            content_words = set(content.split())
            
            # Check for significant word overlap
            overlap = len(fact_words & content_words)
            if overlap >= min(3, len(fact_words) // 2):
                return True
        
        return False
    
    def _log_memory_access(self, operation: str, query: str, user_id: str = None, 
                          results_count: int = 0, error: str = None):
        """Log memory access for audit trail."""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'operation': operation,
            'query_length': len(query),
            'user_id': user_id,
            'results_count': results_count,
            'success': error is None,
            'error': error
        }
        
        self.access_log.append(log_entry)
        
        # Log to existing episodic system
        dao.add_event(
            actor="memory_adapter",
            action=f"memory_{operation}",
            payload=log_entry
        )
```

**Test Plan**:
```bash
# Test memory adapter privacy and validation
pytest tests/test_memory_adapter.py -v

# Adversarial testing
pytest tests/test_memory_adapter.py::test_privacy_protection -v
```

**MVP Gate Criteria**:
- [ ] All memory adapter tests pass including adversarial cases
- [ ] Privacy protection prevents sensitive data access
- [ ] Tombstone filtering works correctly
- [ ] Fact validation against memory functional
- [ ] Comprehensive audit logging for all memory access

**Rollback Plan**: Delete memory_adapter.py and tests

---

### Slice 7.3: /chat API and Message Flow

**Purpose**: Create feature-flagged chat API endpoints with end-to-end message flow through orchestrator.

**Allowed Files**:
- `src/api/chat.py` (create)
- `src/api/schemas.py` (modify)
- `src/api/main.py` (modify)
- `tests/test_chat_api.py` (create)

**MVP Deliverables**:

**Chat API** (`src/api/chat.py`):
```python
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer
from typing import Dict, Any
import uuid
from datetime import datetime

from ..agents.orchestrator import RuleBasedOrchestrator
from ..core.config import config
from .schemas import ChatMessageRequest, ChatMessageResponse, ChatSessionResponse
from ..core import dao

# Feature flag check
if not config.CHAT_API_ENABLED:
    raise ImportError("Chat API disabled - set CHAT_API_ENABLED=true to enable")

router = APIRouter()
security = HTTPBearer()

# Initialize orchestrator with swarm
orchestrator = RuleBasedOrchestrator()

@router.post("/chat/message", response_model=ChatMessageResponse)
async def send_chat_message(
    request: ChatMessageRequest,
    token: str = Depends(security)
) -> ChatMessageResponse:
    """
    Send message through orchestrator swarm with strict validation.
    All responses validated against canonical memory.
    """
    try:
        # Input validation
        if len(request.content.strip()) == 0:
            raise HTTPException(status_code=400, detail="Message content cannot be empty")
        
        if len(request.content) > 2000:  # Reasonable limit for MVP
            raise HTTPException(status_code=400, detail="Message too long")
        
        # Basic prompt injection detection
        if _detect_basic_prompt_injection(request.content):
            dao.add_event(
                actor="chat_api_security",
                action="prompt_injection_blocked",
                payload={
                    "content_length": len(request.content),
                    "model": config.OLLAMA_MODEL
                }
            )
            raise HTTPException(status_code=400, detail="Message content not allowed")
        
        # Generate session ID if not provided
        session_id = request.session_id or str(uuid.uuid4())
        
        # Process through orchestrator swarm
        response = orchestrator.process_user_message(
            message=request.content,
            session_id=session_id,
            user_id=request.user_id
        )
        
        # Create API response
        chat_response = ChatMessageResponse(
            message_id=str(uuid.uuid4()),
            content=response.content,
            model_used=response.model_used,
            timestamp=datetime.now(),
            confidence=response.confidence,
            processing_time_ms=response.processing_time_ms,
            orchestrator_type="rule_based",
            agents_consulted=response.metadata.get("agents_consulted", []),
            validation_passed=response.metadata.get("validation_passed", False),
            memory_sources=response.metadata.get("memory_sources", [])
        )
        
        # Log successful API interaction
        dao.add_event(
            actor="chat_api",
            action="message_processed",
            payload={
                "session_id": session_id,
                "model": response.model_used,
                "processing_time_ms": response.processing_time_ms,
                "user_id": request.user_id,
                "validation_passed": chat_response.validation_passed,
                "agents_consulted_count": len(chat_response.agents_consulted)
            }
        )
        
        return chat_response
        
    except HTTPException:
        raise
    except Exception as e:
        # Log error
        dao.add_event(
            actor="chat_api_error",
            action="message_processing_failed",
            payload={
                "model": config.OLLAMA_MODEL,
                "error": str(e)
            }
        )
        raise HTTPException(status_code=500, detail="Failed to process message")

@router.get("/chat/health")
async def chat_health():
    """Health check for chat system."""
    try:
        # Check orchestrator status
        agent_count = len(orchestrator.agents)
        
        # Check Ollama connectivity
        from ..agents.ollama_agent import check_ollama_health
        ollama_healthy = check_ollama_health()
        
        return {
            "status": "healthy" if ollama_healthy else "degraded",
            "model": config.OLLAMA_MODEL,
            "agent_count": agent_count,
            "orchestrator_type": "rule_based",
            "ollama_healthy": ollama_healthy,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

def _detect_basic_prompt_injection(content: str) -> bool:
    """Basic prompt injection detection for MVP."""
    injection_patterns = [
        "ignore previous instructions",
        "forget everything above",
        "system:",
        "<|im_start|>",
        "### instruction:",
        "[inst]",
        "{{",
        "}}",
        "<script>",
        "javascript:",
        "eval("
    ]
    
    content_lower = content.lower()
    return any(pattern in content_lower for pattern in injection_patterns)
```

**Enhanced Schemas** (`src/api/schemas.py` additions):
```python
class ChatMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)
    session_id: Optional[str] = Field(None, description="Session ID (auto-generated if not provided)")
    user_id: Optional[str] = Field(None, description="User identifier")

class ChatMessageResponse(BaseModel):
    message_id: str
    content: str
    model_used: str
    timestamp: datetime
    confidence: float
    processing_time_ms: int
    orchestrator_type: str = "rule_based"
    agents_consulted: List[str]
    validation_passed: bool
    memory_sources: List[str]
```

**Test Plan**:
```bash
# Test chat API end-to-end
CHAT_API_ENABLED=true SWARM_ENABLED=true pytest tests/test_chat_api.py -v

# Manual curl test
curl -X POST http://localhost:8000/chat/message \
  -H "Authorization: Bearer admin_token" \
  -H "Content-Type: application/json" \
  -d '{"content": "Hello, what can you tell me?"}'
```

**MVP Gate Criteria**:
- [ ] Chat API responds with validated answers
- [ ] End-to-end flow through orchestrator works
- [ ] All responses include validation status
- [ ] Prompt injection detection blocks malicious input
- [ ] Comprehensive logging for all API interactions
- [ ] Zero tolerance for unvalidated responses

**Rollback Plan**: Remove chat API routes and schemas

---

### Slice 7.4: Plugins/Tools (Optional for MVP)

**Purpose**: Simple math plugin for MVP if time permits, with orchestrator validation.

**Allowed Files**:
- `src/agents/plugins.py` (create - only if time permits)
- `tests/test_agent_plugins.py` (create - only if time permits)

**MVP Deliverables** (Time Permitting):

**Simple Plugin System** (`src/agents/plugins.py`):
```python
from typing import Dict, Any, Optional
from dataclasses import dataclass
import time
import math

@dataclass
class PluginResult:
    result: Any
    success: bool
    error: Optional[str] = None
    execution_time_ms: int = 0

class MathPlugin:
    """
    Simple math plugin for MVP.
    Only basic operations, heavily validated.
    """
    
    def __init__(self):
        self.allowed_operations = {
            "add": lambda x, y: x + y,
            "subtract": lambda x, y: x - y,
            "multiply": lambda x, y: x * y,
            "divide": lambda x, y: x / y if y != 0 else None
        }
    
    def execute(self, operation: str, operands: list) -> PluginResult:
        """Execute math operation with safety limits."""
        start_time = time.time()
        
        try:
            # Validate operation
            if operation not in self.allowed_operations:
                return PluginResult(
                    result=None,
                    success=False,
                    error=f"Operation {operation} not allowed",
                    execution_time_ms=int((time.time() - start_time) * 1000)
                )
            
            # Validate operands
            if len(operands) != 2:
                return PluginResult(
                    result=None,
                    success=False,
                    error="Exactly 2 operands required",
                    execution_time_ms=int((time.time() - start_time) * 1000)
                )
            
            # Safety limits
            for operand in operands:
                if not isinstance(operand, (int, float)) or abs(operand) > 1000000:
                    return PluginResult(
                        result=None,
                        success=False,
                        error="Operand out of safe range",
                        execution_time_ms=int((time.time() - start_time) * 1000)
                    )
            
            # Execute operation
            func = self.allowed_operations[operation]
            result = func(operands[0], operands[1])
            
            if result is None:
                return PluginResult(
                    result=None,
                    success=False,
                    error="Division by zero",
                    execution_time_ms=int((time.time() - start_time) * 1000)
                )
            
            return PluginResult(
                result=result,
                success=True,
                execution_time_ms=int((time.time() - start_time) * 1000)
            )
            
        except Exception as e:
            return PluginResult(
                result=None,
                success=False,
                error=str(e),
                execution_time_ms=int((time.time() - start_time) * 1000)
            )

# Plugin registry for orchestrator
AVAILABLE_PLUGINS = {
    "math": MathPlugin()
}
```

**MVP Gate Criteria** (If Implemented):
- [ ] Math plugin executes safely with limits
- [ ] All plugin outputs validated by orchestrator
- [ ] Plugin failures don't crash system
- [ ] Feature can be disabled via flag

**Rollback Plan**: Delete plugins.py and tests (optional feature)

---

### Slice 7.5: Session, Logs, and Quick Swap Documentation

**Purpose**: Session management, log review, and model swapping documentation for MVP completion.

**Allowed Files**:
- `src/core/session.py` (create)
- `tests/test_session.py` (create)
- `docs/FRONTEND_API_CONTRACT.md` (create)
- `docs/MODEL_SWAPPING.md` (create)
- `examples/chat_demo.py` (create)

**MVP Deliverables**:

**Session Management** (`src/core/session.py`):
```python
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import uuid
import json
from ..core import dao
from ..core.config import config

@dataclass
class ChatSession:
    session_id: str
    user_id: Optional[str]
    model_name: str
    created_at: datetime
    last_activity: datetime
    message_count: int = 0
    status: str = "active"

class SessionManager:
    """MVP session management with model tracking."""
    
    def __init__(self):
        self.active_sessions: Dict[str, ChatSession] = {}
        self.session_timeout = timedelta(minutes=30)  # MVP timeout
    
    def create_session(self, user_id: Optional[str] = None) -> ChatSession:
        """Create new session with model tracking."""
        session_id = str(uuid.uuid4())
        session = ChatSession(
            session_id=session_id,
            user_id=user_id,
            model_name=config.OLLAMA_MODEL,
            created_at=datetime.now(),
            last_activity=datetime.now()
        )
        
        self.active_sessions[session_id] = session
        
        # Log session creation
        dao.add_event(
            actor="session_manager",
            action="session_created",
            payload=asdict(session)
        )
        
        return session
    
    def get_session(self, session_id: str) -> Optional[ChatSession]:
        """Get session with expiration check."""
        if session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            
            # Check expiration
            if datetime.now() - session.last_activity > self.session_timeout:
                session.status = "expired"
                del self.active_sessions[session_id]
                return None
            
            return session
        
        return None
```

**Frontend API Contract** (`docs/FRONTEND_API_CONTRACT.md`):
```markdown
# MVP Chat API Contract

## Single Model Control
Change entire system model by setting:
```bash
export OLLAMA_MODEL=liquid-rag:latest  # Default
# export OLLAMA_MODEL=gemma:2b         # Alternative
```

## Chat Endpoint
```http
POST /chat/message
Authorization: Bearer <token>
Content-Type: application/json

{
  "content": "Your question here",
  "session_id": "optional-uuid",
  "user_id": "optional-user-id"
}
```

## Response Format
```json
{
  "message_id": "uuid",
  "content": "Validated response from swarm",
  "model_used": "liquid-rag:latest",
  "timestamp": "2024-01-01T12:00:00Z",
  "confidence": 0.85,
  "processing_time_ms": 1234,
  "orchestrator_type": "rule_based",
  "agents_consulted": ["agent_1", "agent_2", "agent_3", "agent_4"],
  "validation_passed": true,
  "memory_sources": ["memory", "vector_search"]
}
```

## Model Swapping
1. Stop API server
2. `export OLLAMA_MODEL=new_model`
3. Restart API server
4. All responses now use new model
```

**Chat Demo Script** (`examples/chat_demo.py`):
```python
#!/usr/bin/env python3
"""MVP Chat Demo Script"""

import requests
import json

def demo_chat():
    base_url = "http://localhost:8000"
    token = "admin_token"
    
    # Test message
    response = requests.post(
        f"{base_url}/chat/message",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        },
        json={
            "content": "What can you help me with?",
            "user_id": "demo_user"
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Chat Response:")
        print(f"Model: {data['model_used']}")
        print(f"Content: {data['content']}")
        print(f"Validation: {'✅' if data['validation_passed'] else '❌'}")
        print(f"Agents: {', '.join(data['agents_consulted'])}")
    else:
        print(f"❌ Error: {response.text}")

if __name__ == "__main__":
    demo_chat()
```

**Test Plan**:
```bash
# Test session management
pytest tests/test_session.py -v

# Test complete MVP flow
python examples/chat_demo.py
```

**MVP Gate Criteria**:
- [ ] Sessions created and managed correctly
- [ ] Model swap documentation accurate
- [ ] Demo script works end-to-end
- [ ] All logs reviewable by admin
- [ ] Frontend API contract complete

**Rollback Plan**: Delete session management and documentation files

## Global MVP Testing and Verification

### MVP Test Suite
```bash
# Complete MVP test run
make test-mvp-stage7

# Manual verification
SWARM_ENABLED=true CHAT_API_ENABLED=true python examples/chat_demo.py

# Model swap test
export OLLAMA_MODEL=gemma:2b
# Restart and test again
```

### MVP Completion Checklist
- [ ] **Rule-based orchestrator** manages 4+ Ollama agents
- [ ] **Memory validation** prevents hallucinations
- [ ] **Privacy protection** enforced at adapter layer  
- [ ] **API endpoints** functional and secure
- [ ] **Session management** working
- [ ] **Model swapping** via single variable
- [ ] **Comprehensive logging** for all operations
- [ ] **Demo script** proves end-to-end functionality

## MVP Success Criteria

### Functional Success
- ✅ **Working chatbot** responds to user queries through validated swarm
- ✅ **Memory validation** ensures responses traceable to canonical data
- ✅ **Privacy protection** prevents sensitive data exposure
- ✅ **Model swapping** works with single environment variable change

### Safety Success  
- ✅ **No hallucinations** - all responses memory-validated or clarification requests
- ✅ **Comprehensive audit** - every decision and validation logged
- ✅ **Privacy compliance** - sensitive data never reaches agents
- ✅ **Secure API** - prompt injection protection and input validation

### MVP Delivery Success
- ✅ **Tonight ready** - functional chatbot for demo and frontend integration
- ✅ **Frontend ready** - complete API contract and examples
- ✅ **Scalable foundation** - ready for future enhancements
- ✅ **Educational value** - transparent operation with full audit trails

---

**⚠️ STAGE 7 MVP LOCKDOWN COMPLETE - READY FOR TONIGHT DELIVERY ⚠️**

This MVP-focused lockdown ensures rapid delivery of a production-ready, rule-based orchestrator managing an Ollama agent swarm with strict memory validation, comprehensive privacy protection, and single-point model swapping - all ready for demo and frontend integration tonight.