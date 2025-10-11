"""
Stage 3: Bot Swarm Orchestration - Planning Agent (Manager)
Responsible for creating execution plans and coordinating agent tool calls.

The PlanningAgent (Manager):
1. Analyzes user queries to understand intent and requirements
2. Breaks complex queries into manageable steps
3. Determines which tools/agents to involve (semantic.query, kv.get/set, etc.)
4. Creates structured execution plans with tool call sequences
5. Provides planning rationale for audit trail
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime

from ..core.config import SEMANTIC_ENABLED, VECTOR_ENABLED


@dataclass
class ExecutionStep:
    """Represents a single step in the execution plan."""
    tool: str  # Tool name (semantic.query, kv.get, etc.)
    parameters: Dict[str, Any]  # Tool parameters
    description: str  # Human-readable description
    required: bool = True  # Whether this step must succeed
    fallback: Optional[str] = None  # Fallback tool if this fails


@dataclass
class ExecutionPlan:
    """Complete execution plan for a user query."""
    query: str
    intent: str  # High-level understanding (recall, update, analyze, etc.)
    complexity: str  # simple, medium, complex
    steps: List[ExecutionStep]
    rationale: str  # Why this plan was chosen
    confidence: float  # Planning confidence (0-1)
    created_at: datetime


class PlanningAgent:
    """
    Planning Agent that creates structured execution plans for multi-tool queries.

    Supports various query types:
    - Memory recall (name, preferences, history)
    - Memory updates (set preferences, learn facts)
    - Analysis (compare memories, find patterns)
    - Complex multi-part questions
    """

    def __init__(self):
        """Initialize the planning agent."""
        self.max_steps = 5  # Limit plan complexity
        self.supported_tools = {
            "semantic.query": "Search semantic memory for relevant facts",
            "kv.get": "Retrieve exact canonical facts from KV store",
            "kv.set": "Update canonical facts (requires orchestrator permission)",
            "reason.analyze": "Analyze patterns in retrieved data",
            "consolidate": "Merge and reconcile multiple data sources"
        }
        print("🎯 Planning Agent initialized - ready to create execution plans")

    async def create_plan(self, query: str) -> ExecutionPlan:
        """
        Analyze query and create detailed execution plan.

        Args:
            query: User's natural language query

        Returns:
            Structured execution plan with tool call sequence
        """
        # Analyze query intent and complexity
        intent, complexity = self._analyze_intent(query)

        # Create appropriate plan based on intent/complexity
        if intent == "identity_recall":
            steps = self._create_identity_recall_plan(query)
        elif intent == "preference_recall":
            steps = self._create_preference_recall_plan(query)
        elif intent == "memory_update":
            steps = self._create_memory_update_plan(query)
        elif intent == "analysis":
            steps = self._create_analysis_plan(query)
        elif intent == "complex_multi":
            steps = self._create_complex_plan(query)
        else:
            steps = self._create_fallback_plan(query)

        # Generate rationale
        rationale = self._generate_rationale(intent, complexity, steps)

        # Calculate confidence
        confidence = self._calculate_confidence(steps, query)

        return ExecutionPlan(
            query=query,
            intent=intent,
            complexity=complexity,
            steps=steps,
            rationale=rationale,
            confidence=confidence,
            created_at=datetime.now()
        )

    def _analyze_intent(self, query: str) -> tuple[str, str]:
        """
        Analyze query to determine intent and complexity.

        Returns:
            (intent, complexity) tuple
        """
        query_lower = query.lower()

        # Intent classification
        if any(word in query_lower for word in ["who am i", "what's my name", "my name", "displayname"]):
            intent = "identity_recall"
        elif any(word in query_lower for word in ["favorite", "prefer", "like", "timezone", "location"]):
            intent = "preference_recall"
        elif any(word in query_lower for word in ["remember", "set", "update", "change", "save"]):
            intent = "memory_update"
        elif any(word in query_lower for word in ["compare", "analyze", "pattern", "how do i feel", "trend"]):
            intent = "analysis"
        elif len(query.split()) > 10 or "?" in query:  # Complex queries
            intent = "complex_multi"
        else:
            intent = "simple_recall"

        # Complexity assessment
        word_count = len(query.split())
        question_count = query.count("?")
        tool_count_needed = self._estimate_tools_needed(intent)

        if word_count < 5 and question_count <= 1 and tool_count_needed == 1:
            complexity = "simple"
        elif word_count < 15 and question_count <= 2 and tool_count_needed <= 2:
            complexity = "medium"
        else:
            complexity = "complex"

        return intent, complexity

    def _create_identity_recall_plan(self, query: str) -> List[ExecutionStep]:
        """Create plan for identity-related questions."""
        return [
            ExecutionStep(
                tool="kv.get",
                parameters={"key": "displayName"},
                description="Retrieve user's display name from canonical KV store"
            ),
            ExecutionStep(
                tool="semantic.query",
                parameters={"text": "user identity name", "k": 2},
                description="Check for any semantic matches about user identity"
            ),
            ExecutionStep(
                tool="consolidate",
                parameters={"sources": ["kv_result", "semantic_result"]},
                description="Merge KV and semantic results for identity"
            )
        ]

    def _create_preference_recall_plan(self, query: str) -> List[ExecutionStep]:
        """Create plan for preference questions."""
        query_lower = query.lower()
        preference_keys = []

        # Identify specific preferences mentioned
        if "color" in query_lower:
            preference_keys.append("favorite_color")
        if "timezone" in query_lower or "time" in query_lower:
            preference_keys.append("timezone")

        steps = []

        # Add specific KV retrieval steps
        for key in preference_keys:
            steps.append(ExecutionStep(
                tool="kv.get",
                parameters={"key": key},
                description=f"Retrieve {key} from canonical KV store"
            ))

        # Add semantic search if needed
        if len(preference_keys) <= 1:  # If we didn't identify specific keys
            steps.append(ExecutionStep(
                tool="semantic.query",
                parameters={"text": query, "k": 3},
                description="Search semantic memory for preference-related information"
            ))

        # Add consolidation
        steps.append(ExecutionStep(
            tool="consolidate",
            parameters={"sources": ["kv_results", "semantic_result"]},
            description="Merge preference data from all sources"
        ))

        return steps

    def _create_memory_update_plan(self, query: str) -> List[ExecutionStep]:
        """Create plan for memory updates (set operations)."""
        # Extract what needs to be set
        # This is a simplified example - real implementation would parse more
        return [
            ExecutionStep(
                tool="reason.analyze",
                parameters={"task": "extract_update_parameters", "query": query},
                description="Analyze query to extract what should be updated"
            ),
            ExecutionStep(
                tool="kv.set",
                parameters={"requires_approval": True},  # Orchestrator will handle permission
                description="Update canonical KV store (requires orchestrator approval)"
            ),
            ExecutionStep(
                tool="semantic.query",
                parameters={"text": "existing_related_facts", "k": 2},
                description="Check for conflicting semantic facts"
            )
        ]

    def _create_analysis_plan(self, query: str) -> List[ExecutionStep]:
        """Create plan for analysis/comparison questions."""
        return [
            ExecutionStep(
                tool="semantic.query",
                parameters={"text": query, "k": 5},
                description="Retrieve relevant semantic facts for analysis"
            ),
            ExecutionStep(
                tool="kv.get",
                parameters={"pattern": "relevant_*"},  # Get related KV entries
                description="Retrieve related canonical facts"
            ),
            ExecutionStep(
                tool="reason.analyze",
                parameters={"task": "analyze_patterns", "data": "results"},
                description="Analyze patterns and relationships in retrieved data"
            ),
            ExecutionStep(
                tool="consolidate",
                parameters={"sources": ["semantic_results", "kv_results", "analysis"]},
                description="Synthesize comprehensive analysis"
            )
        ]

    def _create_complex_plan(self, query: str) -> List[ExecutionStep]:
        """Create plan for complex multi-part questions."""
        return [
            ExecutionStep(
                tool="reason.analyze",
                parameters={"task": "decompose_query", "query": query},
                description="Break down complex query into components"
            ),
            ExecutionStep(
                tool="semantic.query",
                parameters={"text": "main_topic", "k": 5},
                description="Search for information about main topic"
            ),
            ExecutionStep(
                tool="kv.get",
                parameters={"keys": "relevant_canonical_facts"},
                description="Retrieve specific canonical facts needed"
            ),
            ExecutionStep(
                tool="reason.analyze",
                parameters={"task": "synthesize_answers", "data": "all_results"},
                description="Synthesize answers from multiple sources"
            ),
            ExecutionStep(
                tool="consolidate",
                parameters={"sources": ["all_results"]},
                description="Final consolidation of complex query results"
            )
        ]

    def _create_fallback_plan(self, query: str) -> List[ExecutionStep]:
        """Create simple fallback plan for unrecognized queries."""
        return [
            ExecutionStep(
                tool="semantic.query",
                parameters={"text": query, "k": 3},
                description="Search semantic memory for relevant information"
            ),
            ExecutionStep(
                tool="reason.analyze",
                parameters={"task": "evaluate_relevance", "data": "semantic_results"},
                description="Evaluate if semantic results are relevant"
            )
        ]

    def _estimate_tools_needed(self, intent: str) -> int:
        """Estimate how many tools a query intent typically needs."""
        tool_counts = {
            "identity_recall": 3,  # KV get + semantic + consolidate
            "preference_recall": 2,  # KV get + semantic (sometimes)
            "memory_update": 2,  # Analysis + KV set
            "analysis": 4,  # Multiple queries + analysis + consolidate
            "complex_multi": 5,  # Full analysis pipeline
            "simple_recall": 1  # Just semantic or just KV
        }
        return tool_counts.get(intent, 2)

    def _generate_rationale(self, intent: str, complexity: str, steps: List[ExecutionStep]) -> str:
        """Generate human-readable explanation for the chosen plan."""
        tool_names = [step.tool for step in steps]
        tool_count = len(steps)

        rationale = f"This {complexity} {intent} query requires {tool_count} tools ({', '.join(tool_names)}). "

        if intent == "identity_recall":
            rationale += "Identity questions prioritize canonical KV facts with semantic backup."
        elif intent == "preference_recall":
            rationale += "Preference questions search both specific KV keys and semantic patterns."
        elif intent == "memory_update":
            rationale += "Memory updates require careful validation before canonical changes."
        elif intent == "analysis":
            rationale += "Analysis questions need comprehensive data retrieval and pattern recognition."
        else:
            rationale += f"Plan uses {tool_count} tools to safely retrieve and synthesize information."

        return rationale

    def _calculate_confidence(self, steps: List[ExecutionStep], query: str) -> float:
        """Calculate planning confidence based on plan characteristics."""
        confidence = 0.8  # Base confidence

        # Adjust for complexity
        if len(steps) > 3:
            confidence -= 0.1  # More steps = more potential failure points

        # Adjust for tool diversity
        unique_tools = len(set(step.tool for step in steps))
        if unique_tools >= 3:
            confidence += 0.1  # Multiple tools = more robust

        # Adjust for required tools availability
        available_tools = sum(1 for tool_name in self.supported_tools.keys()
                            if any(s.tool == tool_name for s in steps))
        if available_tools == len(steps):
            confidence += 0.1  # All tools are supported

        return max(0.1, min(1.0, confidence))  # Clamp to 0.1-1.0

    async def health_check(self) -> bool:
        """Check if planning agent is functional."""
        try:
            # Test basic planning capability
            test_plan = await self.create_plan("What is my name?")
            return len(test_plan.steps) > 0 and test_plan.confidence > 0.1
        except Exception:
            return False
