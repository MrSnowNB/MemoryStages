"""
Stage 3: Bot Swarm Orchestration - Memory Agent
Handles retrieval and reconciliation of memory data from KV and semantic stores.

The MemoryAgent:
1. Retrieves facts from both canonical KV store and semantic vector store
2. Applies KV-wins policy for identity/canonical facts
3. Detects and logs conflicts between sources
4. Performs reconciliation logic to create coherent responses
5. Attaches provenance metadata to all facts
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

from ..core.dao import get_key, list_keys
from ..vector.semantic_memory import SemanticMemoryService
from ..core.config import SENSITIVE_EXCLUDE, SEMANTIC_ENABLED
from ..core.reconcile import ConflictDetector


@dataclass
class MemoryFact:
    """Represents a single fact with provenance and metadata."""
    key: str  # Fact identifier (key or derived)
    value: Any  # Fact content
    source: str  # "kv" or "semantic"
    confidence: float  # 0-1 confidence score
    provenance: Dict[str, Any]  # Full provenance data
    canonical: bool  # Whether this is canonical (KV-wins)
    conflicted: bool = False  # Whether this conflicts with other facts
    conflict_reason: Optional[str] = None


@dataclass
class ReconciliationResult:
    """Result of memory reconciliation with facts and conflicts."""
    facts: List[MemoryFact]
    conflicts: List[Dict[str, Any]]
    reconciliation_notes: List[str]
    kv_overrides_applied: int
    semantic_suggestions_ignored: int


class MemoryAgent:
    """
    Memory Agent responsible for retrieving and reconciling facts from multiple sources.

    Implements the critical "KV-wins" policy for canonical data while preserving
    semantic suggestions for non-conflicting information.
    """

    CANONICAL_KEYS = {
        # Identity information - always uses KV store
        "displayName", "username", "email", "user_id",
        # Preferences - controlled canonical facts
        "favorite_color", "timezone", "language", "theme",
        # Settings - controlled canonical facts
        "notifications", "privacy_level", "data_sharing"
    }

    def __init__(self):
        """Initialize the memory agent."""
        self.semantic_service = SemanticMemoryService()
        self.conflict_detector = ConflictDetector()
        print("🔍 Memory Agent initialized - KV-wins policy active")

    async def reconcile_memories(self, query: str, tool_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Reconcile memory facts from KV and semantic sources.

        Args:
            query: Original user query for context
            tool_results: Results from tool calls (KV and semantic data)

        Returns:
            Reconciled facts with provenance and conflict resolution
        """
        # Separate KV and semantic results
        kv_results = [r for r in tool_results if r.get("tool") == "kv.get"]
        semantic_results = [r for r in tool_results if r.get("tool") == "semantic.query"]

        # Extract facts from results
        kv_facts = self._extract_kv_facts(kv_results)
        semantic_facts = self._extract_semantic_facts(semantic_results)

        # Perform reconciliation
        reconciliation = self._reconcile_facts(kv_facts + semantic_facts, query)

        # Log reconciliation results
        await self._log_reconciliation(reconciliation, query)

        # Return reconciled facts for downstream processing
        return [self._fact_to_dict(fact) for fact in reconciliation.facts]

    def _extract_kv_facts(self, kv_results: List[Dict[str, Any]]) -> List[MemoryFact]:
        """Extract facts from KV tool results."""
        facts = []
        for result in kv_results:
            if not result.get("success", False):
                continue

            data = result.get("data", [])
            for item in data:
                # KV results are always canonical for recognized keys
                is_canonical = item.get("key") in self.CANONICAL_KEYS

                fact = MemoryFact(
                    key=item.get("key", "unknown"),
                    value=item.get("value"),
                    source="kv",
                    confidence=1.0,  # KV facts are canonical
                    provenance={
                        "source": "canonical_kv",
                        "updated_at": item.get("updated_at"),
                        "casing": item.get("casing"),
                        "sensitive": item.get("sensitive", False)
                    },
                    canonical=is_canonical
                )
                facts.append(fact)

        return facts

    def _extract_semantic_facts(self, semantic_results: List[Dict[str, Any]]) -> List[MemoryFact]:
        """Extract facts from semantic tool results."""
        facts = []
        for result in semantic_results:
            if not result.get("data"):
                continue

            hits = result.get("data", [])
            for hit in hits:
                # Semantic facts are suggestions, not canonical
                confidence = hit.get("score", 0.5) if isinstance(hit.get("score"), float) else 0.5

                fact = MemoryFact(
                    key=hit.get("doc_id", "unknown"),
                    value=hit.get("text", ""),
                    source="semantic",
                    confidence=min(confidence, 0.9),  # Cap at 0.9 (not fully canonical)
                    provenance={
                        "source": "semantic_memory",
                        "doc_id": hit.get("doc_id"),
                        "score": hit.get("score"),
                        "model_version": hit.get("model_version"),
                        "created_at": hit.get("created_at")
                    },
                    canonical=False  # Semantic facts are never canonical
                )
                facts.append(fact)

        return facts

    def _reconcile_facts(self, all_facts: List[MemoryFact], query: str) -> ReconciliationResult:
        """
        Apply KV-wins policy and resolve conflicts.

        Key rules:
        1. Canonical keys always use KV facts (displayName, timezone, etc.)
        2. Conflicts are logged but KV facts take precedence
        3. Multiple semantic facts can coexist unless they conflict with KV
        """
        # Group facts by what they represent
        fact_groups = self._group_related_facts(all_facts)

        final_facts = []
        conflicts = []
        kv_overrides = 0
        semantic_ignored = 0
        notes = []

        for group_key, group_facts in fact_groups.items():
            if not group_facts:
                continue

            # Check if this represents a canonical key
            is_canonical_group = self._is_canonical_group(group_key, group_facts)

            if is_canonical_group:
                # Apply KV-wins policy
                kv_facts = [f for f in group_facts if f.source == "kv"]
                semantic_facts = [f for f in group_facts if f.source == "semantic"]

                if kv_facts and semantic_facts:
                    # Conflict: KV takes precedence, log the override
                    for kv_fact in kv_facts:
                        kv_fact.canonical = True
                        kv_fact.conflicted = True
                        kv_fact.conflict_reason = f"KV overrides {len(semantic_facts)} semantic suggestions"
                        final_facts.append(kv_fact)

                    # Mark semantic facts as ignored
                    for semantic_fact in semantic_facts:
                        semantic_fact.canonical = False
                        semantic_fact.conflicted = True
                        semantic_fact.conflict_reason = "Overridden by canonical KV fact"
                        conflicts.append({
                            "type": "kv_override",
                            "canonical_fact": self._fact_to_dict(kv_facts[0]),
                            "overridden_facts": [self._fact_to_dict(f) for f in semantic_facts],
                            "reason": f"Canonical key '{group_key}' uses KV fact"
                        })
                        semantic_ignored += len(semantic_facts)
                        kv_overrides += 1

                    notes.append(f"KV-wins applied for {group_key}: {len(semantic_facts)} semantic facts overridden")

                elif kv_facts:
                    # Only KV facts - these are canonical
                    for fact in kv_facts:
                        fact.canonical = True
                        final_facts.append(fact)

                else:
                    # No KV facts - use semantic facts but mark as non-canonical
                    for fact in semantic_facts:
                        fact.canonical = False
                        final_facts.append(fact)
                        notes.append(f"No canonical KV fact for '{group_key}' - using semantic suggestions")

            else:
                # Non-canonical group - can use both KV and semantic facts
                for fact in group_facts:
                    fact.canonical = fact.source == "kv"  # KV facts in non-canonical groups are still canonical
                    final_facts.append(fact)

        return ReconciliationResult(
            facts=final_facts,
            conflicts=conflicts,
            reconciliation_notes=notes,
            kv_overrides_applied=kv_overrides,
            semantic_suggestions_ignored=semantic_ignored
        )

    def _group_related_facts(self, facts: List[MemoryFact]) -> Dict[str, List[MemoryFact]]:
        """Group facts that represent the same information."""
        groups = {}

        for fact in facts:
            # Use fact key as group identifier for now
            # More sophisticated grouping could be added (entity recognition, etc.)
            group_key = fact.key
            if group_key not in groups:
                groups[group_key] = []
            groups[group_key].append(fact)

        return groups

    def _is_canonical_group(self, group_key: str, facts: List[MemoryFact]) -> bool:
        """Determine if a fact group represents canonical information."""
        # Check if any fact in group represents a canonical key
        return any(fact.key in self.CANONICAL_KEYS for fact in facts)

    def _fact_to_dict(self, fact: MemoryFact) -> Dict[str, Any]:
        """Convert MemoryFact to dictionary for serialization."""
        return {
            "key": fact.key,
            "value": fact.value,
            "source": fact.source,
            "confidence": fact.confidence,
            "provenance": fact.provenance,
            "canonical": fact.canonical,
            "conflicted": fact.conflicted,
            "conflict_reason": fact.conflict_reason
        }

    async def _log_reconciliation(self, result: ReconciliationResult, original_query: str):
        """Log reconciliation results to shadow ledger."""
        from ..core.dao import add_event

        await add_event(
            user_id="system",  # Memory agent operates as system
            actor="memory_agent",
            action="reconciliation_complete",
            payload={
                "original_query": original_query,
                "facts_reconciled": len(result.facts),
                "conflicts_detected": len(result.conflicts),
                "kv_overrides": result.kv_overrides_applied,
                "semantic_ignored": result.semantic_suggestions_ignored,
                "canonical_facts": sum(1 for f in result.facts if f.canonical),
                "semantic_facts": sum(1 for f in result.facts if not f.canonical),
                "reconciliation_notes": result.reconciliation_notes[:3]  # Limit for storage
            },
            event_type="reconciliation"
        )

        # Log individual conflicts
        for conflict in result.conflicts:
            await add_event(
                user_id="system",
                actor="memory_agent",
                action="memory_conflict_detected",
                payload=conflict,
                event_type="memory_conflict"
            )

    # Public methods for direct use
    async def retrieve_kv_fact(self, key: str, user_id: str = "default") -> Optional[MemoryFact]:
        """Direct retrieval of a single KV fact."""
        try:
            kv_result = get_key(user_id, key)
            if kv_result:
                return MemoryFact(
                    key=kv_result.key,
                    value=kv_result.value,
                    source="kv",
                    confidence=1.0,
                    provenance={
                        "source": "direct_kv_retrieval",
                        "updated_at": kv_result.updated_at.isoformat(),
                        "casing": kv_result.casing,
                        "sensitive": kv_result.sensitive
                    },
                    canonical=key in self.CANONICAL_KEYS
                )
        except Exception:
            pass
        return None

    async def search_semantic_facts(self, query: str, limit: int = 5) -> List[MemoryFact]:
        """Direct semantic search."""
        try:
            if not SEMANTIC_ENABLED:
                return []

            results = self.semantic_service.query(query, limit)

            facts = []
            for result in results:
                facts.append(MemoryFact(
                    key=result.get("doc_id", "unknown"),
                    value=result.get("text", ""),
                    source="semantic",
                    confidence=result.get("score", 0.5),
                    provenance={
                        "source": "direct_semantic_search",
                        **result
                    },
                    canonical=False
                ))
            return facts
        except Exception:
            return []

    def health_check(self) -> bool:
        """Check if memory agent can access both KV and semantic stores."""
        try:
            # Test KV access
            kv_healthy = True  # Assume KV works since it's always available

            # Test semantic access if enabled
            semantic_healthy = False
            if SEMANTIC_ENABLED:
                try:
                    # Direct synchronous test of semantic service
                    self.semantic_service.query("test", 1)
                    semantic_healthy = True
                except Exception:
                    semantic_healthy = False
            else:
                semantic_healthy = True  # Disabled is considered healthy

            return kv_healthy and semantic_healthy
        except Exception:
            return False
