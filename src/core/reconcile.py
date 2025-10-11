"""
Stage 3: Bot Swarm Orchestration - Conflict Detection and Reconciliation
Handles detection and resolution of conflicts between KV and semantic memory sources.

The reconciler implements the "KV-wins" policy for canonical data while tracking
and logging conflicts between sources for audit and analysis purposes.
"""

from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Conflict:
    """Represents a detected conflict between memory sources."""
    conflict_id: str
    fact_key: str
    kv_value: Any
    semantic_values: List[Any]
    semantic_confidences: List[float]
    rationale: str
    severity: str  # "high", "medium", "low"
    requires_manual_resolution: bool
    created_at: datetime


@dataclass
class ReconciliationSummary:
    """Summary of reconciliation results."""
    total_facts: int
    canonical_facts: int
    semantic_facts: int
    conflicts_detected: int
    kv_overrides: int
    resolution_actions: List[str]


class ConflictDetector:
    """
    Detects conflicts between canonical KV facts and semantic memory suggestions.

    Implements intelligent conflict detection based on:
    - Direct value conflicts for canonical keys
    - Semantic relevance thresholding
    - Confidence level comparisons
    """

    # Keys that must be canonical and cannot have semantic overrides
    STRICT_CANONICAL_KEYS = {
        "displayName", "username", "email", "user_id"
    }

    # Keys that can have semantic suggestions but KV takes precedence
    PREFERENCE_KEYS = {
        "favorite_color", "timezone", "language", "theme",
        "notifications", "privacy_level", "data_sharing"
    }

    def __init__(self):
        self.conflict_history = []
        print("⚖️  Conflict Detector initialized - KV-wins policy enforcement")

    def detect_conflicts(self, kv_facts: List[Dict[str, Any]], semantic_facts: List[Dict[str, Any]]) -> List[Conflict]:
        """
        Detect conflicts between KV and semantic memory sources.

        Args:
            kv_facts: Canonical facts from KV store
            semantic_facts: Suggestions from semantic search

        Returns:
            List of detected conflicts
        """
        conflicts = []

        # Group facts by key for comparison
        kv_by_key = {f.get("key"): f for f in kv_facts if f.get("key")}
        semantic_by_key = {}

        for fact in semantic_facts:
            key = fact.get("key", "unknown")
            if key not in semantic_by_key:
                semantic_by_key[key] = []
            semantic_by_key[key].append(fact)

        # Check each KV fact for conflicts with semantic facts
        for kv_key, kv_fact in kv_by_key.items():
            if kv_key in semantic_by_key:
                semantic_matches = semantic_by_key[kv_key]
                conflict = self._analyze_key_conflict(kv_key, kv_fact, semantic_matches)
                if conflict:
                    conflicts.append(conflict)

        # Look for semantic facts that contradict each other significantly
        conflicts.extend(self._detect_semantic_inconsistencies(semantic_facts))

        return conflicts

    def _analyze_key_conflict(self, key: str, kv_fact: Dict[str, Any], semantic_facts: List[Dict[str, Any]]) -> Optional[Conflict]:
        """Analyze whether a specific key has conflicts between sources."""
        kv_value = str(kv_fact.get("value", "")).lower().strip()
        semantic_values = []
        semantic_confidences = []

        for semantic_fact in semantic_facts:
            semantic_value = str(semantic_fact.get("value", "")).lower().strip()
            semantic_values.append(semantic_value)
            semantic_confidences.append(semantic_fact.get("confidence", 0))

        # Check for exact value conflicts
        conflicting_values = [v for v in semantic_values if v != kv_value and v]

        if not conflicting_values:
            return None  # No conflict

        # Assess conflict severity
        severity = self._assess_conflict_severity(key, kv_fact, semantic_facts)
        requires_manual = self._requires_manual_resolution(key, kv_value, conflicting_values)

        conflict = Conflict(
            conflict_id=f"conflict_{key}_{int(datetime.now().timestamp())}",
            fact_key=key,
            kv_value=kv_fact.get("value"),
            semantic_values=[f.get("value") for f in semantic_facts],
            semantic_confidences=semantic_confidences,
            rationale=self._generate_conflict_rationale(key, kv_value, conflicting_values, severity),
            severity=severity,
            requires_manual_resolution=requires_manual,
            created_at=datetime.now()
        )

        return conflict

    def _assess_conflict_severity(self, key: str, kv_fact: Dict[str, Any], semantic_facts: List[Dict[str, Any]]) -> str:
        """Assess the severity of a conflict."""
        # Strict canonical keys have highest severity
        if key in self.STRICT_CANONICAL_KEYS:
            return "high"

        # Preference keys medium severity
        if key in self.PREFERENCE_KEYS:
            return "medium"

        # Check if any semantic fact has high confidence
        max_semantic_confidence = max((f.get("confidence", 0) for f in semantic_facts), default=0)

        if max_semantic_confidence > 0.8:
            return "medium"
        else:
            return "low"

    def _requires_manual_resolution(self, key: str, kv_value: str, conflicting_values: List[str]) -> bool:
        """Determine if conflict requires manual resolution."""
        # Strict canonical keys never need manual resolution - KV wins
        if key in self.STRICT_CANONICAL_KEYS:
            return False

        # Check if conflict is ambiguous vs clear contradiction
        conflicting_values = list(set(conflicting_values))  # Remove duplicates

        # Multiple conflicting semantic values suggest complexity
        if len(conflicting_values) > 2:
            return True

        # Preference keys with clear contradictions may need review
        if key in self.PREFERENCE_KEYS and len(conflicting_values) > 1:
            return True

        return False

    def _generate_conflict_rationale(self, key: str, kv_value: str, conflicting_values: List[str], severity: str) -> str:
        """Generate a human-readable explanation of the conflict."""
        if key in self.STRICT_CANONICAL_KEYS:
            return f"Strict canonical key '{key}' has contradictory semantic suggestions despite canonical KV value '{kv_value}'."

        if key in self.PREFERENCE_KEYS:
            return f"Preference key '{key}' has KV value '{kv_value}' but semantic memory suggests {len(conflicting_values)} alternative(s): {', '.join(conflicting_values[:3])}."

        return f"Key '{key}' shows discrepancy between canonical value '{kv_value}' and semantic suggestions ({len(conflicting_values)} variants)."

    def _detect_semantic_inconsistencies(self, semantic_facts: List[Dict[str, Any]]) -> List[Conflict]:
        """Detect inconsistencies within semantic facts themselves."""
        conflicts = []

        # Group semantic facts by key
        by_key = {}
        for fact in semantic_facts:
            key = fact.get("key", "unknown")
            if key not in by_key:
                by_key[key] = []
            by_key[key].append(fact)

        # Check each key for internal semantic conflicts
        for key, facts in by_key.items():
            if len(facts) < 2:
                continue

            values = [str(f.get("value", "")).lower().strip() for f in facts]
            confidences = [f.get("confidence", 0) for f in facts]

            unique_values = set(values)
            if len(unique_values) > 1:
                # Multiple different values for same key - internal semantic conflict
                conflict = Conflict(
                    conflict_id=f"semantic_internal_{key}_{int(datetime.now().timestamp())}",
                    fact_key=key,
                    kv_value=None,  # No KV value for internal semantic conflict
                    semantic_values=list(unique_values),
                    semantic_confidences=confidences,
                    rationale=f"Semantic memory contains {len(unique_values)} different values for key '{key}': {', '.join(unique_values)}.",
                    severity="low",  # Internal semantic conflicts are less severe
                    requires_manual_resolution=len(unique_values) > 3,
                    created_at=datetime.now()
                )
                conflicts.append(conflict)

        return conflicts

    def reconcile_fact(self, key: str, kv_fact: Optional[Dict[str, Any]], semantic_facts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Reconcile a single fact with KV-wins policy.

        Returns reconciled fact with conflict metadata.
        """
        result = {
            "key": key,
            "reconciled": True,
            "source": "unknown",
            "canonical": False,
            "conflicted": False,
            "conflict_count": 0,
            "confidence": 0.0
        }

        if kv_fact and not semantic_facts:
            # Pure KV fact - no conflict possible
            result.update({
                "source": "kv",
                "canonical": True,
                "value": kv_fact.get("value"),
                "confidence": kv_fact.get("confidence", 1.0),
                "provenance": kv_fact.get("provenance", {})
            })
            return result

        if not kv_fact and semantic_facts:
            # Pure semantic facts - use highest confidence
            best_semantic = max(semantic_facts, key=lambda x: x.get("confidence", 0))
            result.update({
                "source": "semantic",
                "canonical": False,
                "value": best_semantic.get("value"),
                "confidence": best_semantic.get("confidence", 0.5),
                "provenance": best_semantic.get("provenance", {})
            })
            return result

        if kv_fact and semantic_facts:
            # Potential conflict - analyze
            conflicts = self.detect_conflicts([kv_fact], semantic_facts)
            conflict_count = len(conflicts)

            if conflicts:
                # Conflict exists - KV wins for this key
                result.update({
                    "source": "kv",
                    "canonical": True,
                    "value": kv_fact.get("value"),
                    "confidence": kv_fact.get("confidence", 1.0),
                    "provenance": kv_fact.get("provenance", {}),
                    "conflicted": True,
                    "conflict_count": conflict_count,
                    "conflict_details": [c.rationale for c in conflicts]
                })

                # Store conflict in history
                self.conflict_history.extend(conflicts)
            else:
                # No conflict - KV still canonical but no drama
                result.update({
                    "source": "kv",
                    "canonical": True,
                    "value": kv_fact.get("value"),
                    "confidence": kv_fact.get("confidence", 1.0),
                    "provenance": kv_fact.get("provenance", {})
                })

        return result

    def get_conflict_history(self, key: Optional[str] = None, limit: int = 100) -> List[Conflict]:
        """Retrieve conflict history, optionally filtered by key."""
        conflicts = self.conflict_history
        if key:
            conflicts = [c for c in conflicts if c.fact_key == key]

        return conflicts[-limit:] if limit > 0 else conflicts

    def get_conflict_summary(self) -> Dict[str, Any]:
        """Get summary statistics about conflicts."""
        if not self.conflict_history:
            return {"total_conflicts": 0, "by_key": {}, "by_severity": {}}

        by_key = {}
        by_severity = {"high": 0, "medium": 0, "low": 0}

        for conflict in self.conflict_history:
            # Count by key
            if conflict.fact_key not in by_key:
                by_key[conflict.fact_key] = 0
            by_key[conflict.fact_key] += 1

            # Count by severity
            by_severity[conflict.severity] += 1

        return {
            "total_conflicts": len(self.conflict_history),
            "by_key": by_key,
            "by_severity": by_severity,
            "requires_manual": sum(1 for c in self.conflict_history if c.requires_manual_resolution)
        }

    def health_check(self) -> bool:
        """Check if conflict detector is operational."""
        try:
            # Test conflict detection
            kv_facts = [{"key": "test", "value": "kv_value"}]
            semantic_facts = [{"key": "test", "value": "semantic_value", "confidence": 0.8}]
            conflicts = self.detect_conflicts(kv_facts, semantic_facts)
            return isinstance(conflicts, list)
        except Exception:
            return False
