"""
Stage 3: Bot Swarm Orchestration - Reasoner Agent
Synthesizes final responses from reconciled memory facts with proper citations.

The Reasoner Agent:
1. Receives reconciled facts from MemoryAgent with provenance
2. Analyzes patterns and relationships in the data
3. Generates coherent answers with inline citations
4. Provides confidence scores and reasoning explanations
5. Ensures citations clearly indicate source (KV vs semantic)
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import re


@dataclass
class Citation:
    """Represents a citation in the response."""
    fact_key: str
    source: str  # "kv" or "semantic"
    confidence: float
    canonical: bool
    citation_text: str  # e.g., "[KV: displayName]" or "[Semantic: 85% match]"


@dataclass
class SynthesisInput:
    """Input data for answer synthesis."""
    original_query: str
    facts: List[Dict[str, Any]]
    plan: Any  # From PlanningAgent
    tool_results: List[Dict[str, Any]]
    working_memory: Dict[str, Any]


@dataclass
class SynthesisOutput:
    """Synthesized answer with citations."""
    content: str
    citations: List[Citation]
    confidence: float
    reasoning_path: List[str]  # Steps in reasoning
    provenance: Dict[str, Any]
    synthesis_metadata: Dict[str, Any]


class ReasonerAgent:
    """
    Reasoner Agent that creates human-readable answers from structured memory data.

    Builds coherent responses with inline citations, confidence indicators,
    and clear provenance distinction between canonical (KV) and semantic facts.
    """

    def __init__(self):
        """Initialize the reasoner agent."""
        self.confidence_thresholds = {
            "high": 0.8,
            "medium": 0.6,
            "low": 0.3
        }
        print("🧠 Reasoner Agent initialized - citation synthesis ready")

    async def synthesize_response(self, synthesis_input: SynthesisInput) -> SynthesisOutput:
        """
        Synthesize a comprehensive answer from reconciled facts.

        Args:
            synthesis_input: Facts and context from previous agents

        Returns:
            Synthesized response with citations and provenance
        """
        query = synthesis_input.original_query
        facts = synthesis_input.facts

        # Classify query type to determine synthesis strategy
        query_type = self._classify_query(query)

        # Generate synthesis plan based on query type and available facts
        synthesis_plan = self._create_synthesis_plan(query_type, facts, query)

        # Build the cited answer
        answer_text = self._build_answer_text(synthesis_plan, facts, query)

        # Generate citations for the answer
        citations = self._generate_citations(facts, answer_text)

        # Calculate overall confidence
        confidence = self._calculate_answer_confidence(facts, citations)

        # Create reasoning path
        reasoning_path = self._build_reasoning_path(synthesis_plan, facts, confidence)

        # Compile provenance metadata
        provenance = self._build_provenance(facts, citations)

        return SynthesisOutput(
            content=answer_text,
            citations=citations,
            confidence=confidence,
            reasoning_path=reasoning_path,
            provenance=provenance,
            synthesis_metadata={
                "query_type": query_type,
                "facts_used": len(self._get_used_facts(facts, answer_text)),
                "canonical_facts": sum(1 for f in facts if f.get("canonical", False)),
                "semantic_facts": sum(1 for f in facts if not f.get("canonical", False)),
                "synthesis_strategy": synthesis_plan["strategy"],
                "synthesis_timestamp": datetime.now().isoformat()
            }
        )

    def _classify_query(self, query: str) -> str:
        """Classify the query to determine synthesis strategy."""
        query_lower = query.lower()

        if any(word in query_lower for word in ["who am i", "what's my name", "my name"]):
            return "identity_recall"
        elif any(word in query_lower for word in ["what's my", "tell me about my", "what do i"]):
            return "preference_recall"
        elif any(word in query_lower for word in ["how do i feel", "what did i", "when did i"]):
            return "experience_analysis"
        elif any(word in query_lower for word in ["compare", "versus", "vs", "difference"]):
            return "comparison"
        elif any(word in query_lower for word in ["how", "why", "explain"]):
            return "explanation"
        elif "?" in query:
            return "informational"
        else:
            return "general_recall"

    def _create_synthesis_plan(self, query_type: str, facts: List[Dict[str, Any]], query: str) -> Dict[str, Any]:
        """Create a plan for synthesizing the answer."""
        # Count fact types
        canonical_facts = [f for f in facts if f.get("canonical", False)]
        semantic_facts = [f for f in facts if not f.get("canonical", False)]
        conflicted_facts = [f for f in facts if f.get("conflicted", False)]

        plan = {
            "query_type": query_type,
            "total_facts": len(facts),
            "canonical_count": len(canonical_facts),
            "semantic_count": len(semantic_facts),
            "conflict_count": len(conflicted_facts),
            "strategy": "direct"  # Default strategy
        }

        # Choose synthesis strategy based on data characteristics
        if plan["canonical_count"] > 0 and plan["conflict_count"] > 0:
            plan["strategy"] = "conflict_resolution"
        elif plan["semantic_count"] > plan["canonical_count"]:
            plan["strategy"] = "semantic_integration"
        elif len(canonical_facts) == 1:
            plan["strategy"] = "canonical_focus"
        elif query_type == "identity_recall":
            plan["strategy"] = "identity_synthesis"
        elif query_type == "preference_recall":
            plan["strategy"] = "preference_synthesis"
        elif query_type == "comparison":
            plan["strategy"] = "comparison_analysis"

        return plan

    def _build_answer_text(self, plan: Dict[str, Any], facts: List[Dict[str, Any]], query: str) -> str:
        """Build the natural language answer with embedded citations."""
        strategy = plan["strategy"]

        if strategy == "identity_synthesis":
            return self._synthesize_identity_answer(facts)
        elif strategy == "preference_synthesis":
            return self._synthesize_preference_answer(facts, query)
        elif strategy == "semantic_integration":
            return self._synthesize_semantic_answer(facts, query)
        elif strategy == "canonical_focus":
            return self._synthesize_canonical_answer(facts)
        elif strategy == "conflict_resolution":
            return self._synthesize_conflict_answer(facts, plan["conflict_count"])
        elif strategy == "comparison_analysis":
            return self._synthesize_comparison_answer(facts)
        else:
            return self._synthesize_general_answer(facts, query)

    def _synthesize_identity_answer(self, facts: List[Dict[str, Any]]) -> str:
        """Synthesize answer for identity queries (name, etc.)."""
        # Look for displayName specifically
        name_facts = [f for f in facts if f.get("key") == "displayName"]

        if name_facts:
            fact = name_facts[0]
            confidence_marker = self._get_confidence_marker(fact)
            return f"Your name is {fact['value']}. {confidence_marker}"
        else:
            return "I don't have your name stored in canonical memory. [KV: no_displayName]"

    def _synthesize_preference_answer(self, facts: List[Dict[str, Any]], query: str) -> str:
        """Synthesize answer for preference queries."""
        query_lower = query.lower()
        responses = []

        # Check for specific preferences mentioned in query
        if "color" in query_lower:
            color_facts = [f for f in facts if f.get("key") == "favorite_color"]
            if color_facts:
                fact = color_facts[0]
                marker = "[KV: favorite_color]" if fact.get("canonical") else "[Semantic: color_preference]"
                responses.append(f"Your favorite color is {fact['value']}. {marker}")

        if "time" in query_lower or "timezone" in query_lower:
            tz_facts = [f for f in facts if f.get("key") == "timezone"]
            if tz_facts:
                fact = tz_facts[0]
                marker = "[KV: timezone]" if fact.get("canonical") else "[Semantic: timezone_preference]"
                responses.append(f"Your timezone is {fact['value']}. {marker}")

        if not responses:
            # General preference response
            canonical_prefs = [f for f in facts if f.get("canonical", False)]
            if canonical_prefs:
                pref_text = ", ".join([f"{f['key'].replace('_', ' ')}: {f['value']}" for f in canonical_prefs[:3]])
                responses.append(f"Your stored preferences include: {pref_text}. [KV: preferences]")
            else:
                responses.append("I don't have specific preference information stored for that. [KV: no_matching_preferences]")

        return " ".join(responses)

    def _synthesize_semantic_answer(self, facts: List[Dict[str, Any]], query: str) -> str:
        """Synthesize answer from primarily semantic facts."""
        # Group semantic facts by relevance
        semantic_facts = [f for f in facts if not f.get("canonical", False)]

        if not semantic_facts:
            return "I couldn't find relevant information about that. [Semantic: no_matches]"

        # Take top semantic facts (sorted by confidence)
        top_facts = sorted(semantic_facts, key=lambda x: x.get("confidence", 0), reverse=True)[:3]

        responses = []
        for fact in top_facts:
            confidence = fact.get("confidence", 0)
            score_text = f"{int(confidence * 100)}% match" if confidence < 1.0 else "exact match"

            # Extract relevant part of the fact
            fact_text = fact.get("value", "")[:100]  # Truncate for readability
            if fact_text:
                responses.append(f"{fact_text} [Semantic: {score_text}]")

        return " ".join(responses)

    def _synthesize_canonical_answer(self, facts: List[Dict[str, Any]]) -> str:
        """Synthesize answer from canonical KV facts."""
        canonical_facts = [f for f in facts if f.get("canonical", False)]

        if len(canonical_facts) == 1:
            fact = canonical_facts[0]
            return f"The information you requested is: {fact['value']}. [KV: {fact['key']}]"
        elif len(canonical_facts) > 1:
            fact_summaries = [f"{f['key'].replace('_', ' ')}: {f['value']}" for f in canonical_facts[:3]]
            return f"I found this canonical information: {'; '.join(fact_summaries)}. [KV: multiple_facts]"
        else:
            return "This query requires canonical information that's not currently stored. [KV: information_unavailable]"

    def _synthesize_conflict_answer(self, facts: List[Dict[str, Any]], conflict_count: int) -> str:
        """Synthesize answer when there are known conflicts."""
        # Get unconflicted canonical facts
        canonical_unconflicted = [f for f in facts if f.get("canonical", False) and not f.get("conflicted", False)]

        if canonical_unconflicted:
            fact_text = ". ".join([f"From canonical memory: {f['value']}" for f in canonical_unconflicted[:2]])
            return f"{fact_text} Note: {conflict_count} conflicting semantic suggestions were reconciled in favor of canonical data. [KV: reconciled_with_conflicts]"
        else:
            semantic_facts = [f for f in facts if not f.get("canonical", False)]
            if semantic_facts:
                fact = semantic_facts[0]
                confidence = fact.get("confidence", 0)
                return f"Based on semantic memory (canonical data unavailable): {fact['value'][:100]} [Semantic: {int(confidence*100)}%_{conflict_count}_conflicts_reconciled]"
            else:
                return f"This information has conflicts that require manual reconciliation. {conflict_count} conflicts detected. [Conflict: needs_resolution]"

    def _synthesize_comparison_answer(self, facts: List[Dict[str, Any]]) -> str:
        """Synthesize answer for comparison queries."""
        if len(facts) < 2:
            return "I need more information to make a meaningful comparison. Available facts are limited. [Analysis: insufficient_data]"

        # Group facts by source for comparison
        kv_facts = [f for f in facts if f.get("source") == "kv"]
        semantic_facts = [f for f in facts if f.get("source") == "semantic"]

        comparison_parts = []

        if kv_facts:
            comparison_parts.append(f"Canonical memory contains {len(kv_facts)} relevant facts [KV: {len(kv_facts)}_canonical_facts]")

        if semantic_facts:
            avg_confidence = sum(f.get("confidence", 0) for f in semantic_facts) / len(semantic_facts)
            comparison_parts.append(f"Semantic memory provides {len(semantic_facts)} additional insights (avg {int(avg_confidence*100)}% confidence) [Semantic: {len(semantic_facts)}_insights]")

        return f"Comparison analysis: {'; '.join(comparison_parts)}. The canonical facts take precedence where conflicts exist."

    def _synthesize_general_answer(self, facts: List[Dict[str, Any]], query: str) -> str:
        """Synthesize general-purpose answer."""
        canonical_count = sum(1 for f in facts if f.get("canonical", False))
        semantic_count = sum(1 for f in facts if not f.get("canonical", False))

        if canonical_count > 0:
            # Prioritize canonical facts
            canonical_fact = next((f for f in facts if f.get("canonical", False)), None)
            if canonical_fact:
                return f"Based on stored information: {canonical_fact['value']}. [KV: {canonical_fact['key']}]"
        elif semantic_count > 0:
            # Use semantic facts
            semantic_fact = max(facts, key=lambda x: x.get("confidence", 0))
            confidence = semantic_fact.get("confidence", 0)
            return f"From memory associations: {semantic_fact['value'][:100]} [Semantic: {int(confidence*100)}%_{semantic_count}_total_facts]"
        else:
            return "I don't have relevant information stored for that query. [Memory: no_matching_facts]"

    def _generate_citations(self, facts: List[Dict[str, Any]], answer_text: str) -> List[Citation]:
        """Generate structured citations for facts used in the answer."""
        citations = []

        for fact in facts:
            # Check if this fact is referenced in the answer
            if self._fact_used_in_answer(fact, answer_text):
                citation = Citation(
                    fact_key=fact.get("key", "unknown"),
                    source=fact.get("source", "unknown"),
                    confidence=fact.get("confidence", 0.5),
                    canonical=fact.get("canonical", False),
                    citation_text=self._create_citation_text(fact)
                )
                citations.append(citation)

        return citations

    def _fact_used_in_answer(self, fact: Dict[str, Any], answer_text: str) -> bool:
        """Determine if a fact was used in the answer text."""
        # Simple heuristic: check if fact value appears in answer
        fact_value = str(fact.get("value", "")).lower()
        answer_lower = answer_text.lower()
        return fact_value in answer_lower or fact.get("key", "").lower() in answer_lower

    def _create_citation_text(self, fact: Dict[str, Any]) -> str:
        """Create appropriate citation text."""
        if fact.get("canonical", False):
            key = fact.get("key", "unknown")
            return f"[KV: {key}]"
        else:
            confidence = fact.get("confidence", 0)
            confidence_pct = int(confidence * 100)
            return f"[Semantic: {confidence_pct}% match]"

    def _calculate_answer_confidence(self, facts: List[Dict[str, Any]], citations: List[Citation]) -> float:
        """Calculate overall confidence in the answer."""
        if not facts:
            return 0.0

        # Base confidence from fact quality
        canonical_weight = 1.0
        semantic_weight = 0.7

        weighted_confidence = 0.0
        total_weight = 0.0

        for fact in facts:
            weight = canonical_weight if fact.get("canonical", False) else semantic_weight
            confidence = fact.get("confidence", 0.5)
            weighted_confidence += confidence * weight
            total_weight += weight

        base_confidence = weighted_confidence / total_weight if total_weight > 0 else 0.0

        # Adjust for conflicts
        conflict_penalty = sum(1 for f in facts if f.get("conflicted", False)) * 0.1
        final_confidence = max(0.0, base_confidence - conflict_penalty)

        return final_confidence

    def _build_reasoning_path(self, plan: Dict[str, Any], facts: List[Dict[str, Any]], confidence: float) -> List[str]:
        """Build a reasoning path documenting the synthesis process."""
        path = [
            f"Analyzed query as {plan['query_type']} type",
            f"Found {plan['canonical_count']} canonical and {plan['semantic_count']} semantic facts",
            f"Applied {plan['strategy']} synthesis strategy"
        ]

        if plan['conflict_count'] > 0:
            path.append(f"Resolved {plan['conflict_count']} conflicts")

        confidence_level = "low" if confidence < 0.4 else "medium" if confidence < 0.7 else "high"
        path.append(f"Generated answer with {confidence_level} confidence ({int(confidence*100)}%)")

        return path

    def _build_provenance(self, facts: List[Dict[str, Any]], citations: List[Citation]) -> Dict[str, Any]:
        """Build provenance metadata for the answer."""
        return {
            "facts_used": len(citations),
            "canonical_sources": sum(1 for c in citations if c.canonical),
            "semantic_sources": sum(1 for c in citations if not c.canonical),
            "avg_confidence": sum(c.confidence for c in citations) / len(citations) if citations else 0,
            "citations": [c.citation_text for c in citations],
            "source_breakdown": {
                "kv_facts": sum(1 for f in facts if f.get("source") == "kv"),
                "semantic_facts": sum(1 for f in facts if f.get("source") == "semantic"),
                "highest_confidence": max((f.get("confidence", 0) for f in facts), default=0)
            }
        }

    def _get_used_facts(self, facts: List[Dict[str, Any]], answer_text: str) -> List[Dict[str, Any]]:
        """Get list of facts that were used in the answer."""
        return [f for f in facts if self._fact_used_in_answer(f, answer_text)]

    def _get_confidence_marker(self, fact: Dict[str, Any]) -> str:
        """Get confidence marker for a fact."""
        confidence = fact.get("confidence", 0.5)
        if fact.get("canonical", False):
            return "[Canonical source]"  # KV facts are always authoritative
        elif confidence >= 0.8:
            return "[High confidence match]"
        elif confidence >= 0.6:
            return "[Medium confidence match]"
        else:
            return "[Low confidence match]"

    def health_check(self) -> bool:
        """Check if reasoner agent is functional."""
        try:
            # Simple synchronous test - just verify the agent can be instantiated
            # Full synthesis testing would be too complex for a health check
            return hasattr(self, '_classify_query') and hasattr(self, 'synthesize_response')
        except Exception:
            return False
