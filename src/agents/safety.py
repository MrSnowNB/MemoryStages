"""
Stage 3: Bot Swarm Orchestration - Safety Agent
Provides final validation and safety checks for swarm-generated responses.

The SafetyAgent ensures responses are safe, private, and appropriate by:
1. Pre-validating user inputs for safety concerns
2. Checking generated responses for unsafe content
3. Blocking prompt injection attempts
4. Redacting sensitive PII information
5. Providing safe alternatives when needed
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import re


@dataclass
class SafetyValidation:
    """Result of a safety validation check."""
    allowed: bool
    risk_level: str  # "safe", "caution", "blocked", "redact"
    reason: Optional[str]
    safe_response: Optional[str]
    flagged_terms: List[str]
    validation_metadata: Dict[str, Any]


@dataclass
class SafetyFilterResult:
    """Result of content filtering."""
    clear_text: str
    redacted_content: str
    redaction_count: int
    redaction_reasons: List[str]


class SafetyAgent:
    """
    Safety Agent that validates both inputs and outputs for security and appropriateness.

    Implements multi-layer safety validation:
    - Input sanitization
    - Prompt injection detection
    - Content filtering
    - PII redaction
    - Response safety checking
    """

    # High-risk patterns that should always block
    BLOCK_PATTERNS = [
        r"\b(?:exec|eval|execute|system|shell|cmd|command|script)\s*\(",
        r"\bimport\s+(?:os|sys|subprocess|shutil)",
        r"\b(?:delete|drop|truncate|alter)\s+.*table",
        r"\b(?:rm\s+-rf|format\s+c:|del\s+.*\\\*)",
        r"(?:SELECT|INSERT|UPDATE|DELETE).*\*.*FROM",
        r"<\s*script[^>]*>.*?<\s*/\s*script\s*>",
        r"(?:javascript|vbscript|onload|onerror)\s*:",
        r"\b(?:password|secret|key|token)\s*:",
        r"system\s*\(\s*\)",
        r"os\.\w+\s*\(",
    ]

    # Potentially risky patterns requiring caution
    CAUTION_PATTERNS = [
        r"(?:I\s+am\s+|my\s+name\s+is\s+).*?(?:admin|root|system)",
        r"\b(?:server|database|config|settings)\s+(?:file|path)",
        r"(?:how\s+to|tutorial).*?(?:hack|exploit|jailbreak)",
        r"(?:bypass|override|disable).*?(?:security|filter|safety)",
        r"(?:privileged|admin|sensitive).*?(?:access|information|data)",
    ]

    # PII patterns for redaction
    PII_PATTERNS = [
        (r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b", "phone_number"),
        (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "email"),
        (r"\b\d{3}[-.\s]\d{2}[-.\s]\d{4}\b", "ssn"),
        (r"\b\d{4}[-.\s]\d{4}[-.\s]\d{4}[-.\s]\d{4}\b", "credit_card"),
        (r"\b\d{1,5}\s+\w+\s+\w+,\s+\w+\s+\d{5}\b", "address"),
    ]

    def __init__(self):
        """Initialize the safety agent."""
        self.blocked_attempts = 0
        self.caution_triggers = 0
        self.redactions_performed = 0
        print("🛡️  Safety Agent initialized - multi-layer protection active")

    async def validate_input(self, input_text: str) -> SafetyValidation:
        """
        Validate user input for safety concerns before processing.

        Args:
            input_text: Raw user input

        Returns:
            Safety validation result
        """
        # Check for blocking patterns
        block_matches = self._check_patterns(input_text, self.BLOCK_PATTERNS)
        if block_matches:
            self.blocked_attempts += 1
            return SafetyValidation(
                allowed=False,
                risk_level="blocked",
                reason=f"Input contains blocked security patterns: {', '.join(block_matches[:3])}",
                safe_response="I'm sorry, but I cannot process this request as it appears to contain potentially unsafe content.",
                flagged_terms=block_matches,
                validation_metadata={
                    "check_type": "input_validation",
                    "timestamp": datetime.now().isoformat(),
                    "pattern_type": "block"
                }
            )

        # Check for caution patterns
        caution_matches = self._check_patterns(input_text, self.CAUTION_PATTERNS)
        if caution_matches:
            self.caution_triggers += 1
            return SafetyValidation(
                allowed=True,
                risk_level="caution",
                reason=f"Input contains caution patterns that will be monitored: {', '.join(caution_matches[:3])}",
                safe_response=None,
                flagged_terms=caution_matches,
                validation_metadata={
                    "check_type": "input_validation",
                    "timestamp": datetime.now().isoformat(),
                    "pattern_type": "caution"
                }
            )

        # Input appears safe
        return SafetyValidation(
            allowed=True,
            risk_level="safe",
            reason="Input passed safety validation",
            safe_response=None,
            flagged_terms=[],
            validation_metadata={
                "check_type": "input_validation",
                "timestamp": datetime.now().isoformat(),
                "pattern_type": "safe"
            }
        )

    async def validate_output(self, output_text: str, context: Optional[Dict[str, Any]] = None) -> SafetyValidation:
        """
        Validate generated output for safety and appropriateness.

        Args:
            output_text: Generated response text
            context: Optional context about the generation

        Returns:
            Safety validation result
        """
        # Check for PII that should be redacted
        pii_filter = self._filter_pii(output_text)
        if pii_filter.redaction_count > 0:
            self.redactions_performed += 1
            return SafetyValidation(
                allowed=True,
                risk_level="redact",
                reason=f"Output contains {pii_filter.redaction_count} PII items that were redacted",
                safe_response=pii_filter.clear_text,
                flagged_terms=pii_filter.redaction_reasons,
                validation_metadata={
                    "check_type": "output_validation",
                    "timestamp": datetime.now().isoformat(),
                    "filter_type": "pii_redaction",
                    "redactions": pii_filter.redaction_count
                }
            )

        # Check for content that should be blocked
        block_matches = self._check_patterns(output_text, self.BLOCK_PATTERNS)
        if block_matches:
            return SafetyValidation(
                allowed=False,
                risk_level="blocked",
                reason=f"Generated output contains unsafe content: {', '.join(block_matches[:3])}",
                safe_response="I'm sorry, but I must provide a safer response due to content guidelines.",
                flagged_terms=block_matches,
                validation_metadata={
                    "check_type": "output_validation",
                    "timestamp": datetime.now().isoformat(),
                    "filter_type": "content_block"
                }
            )

        # Check for responses that might indicate jailbreak/hallucination
        hallucination_indicators = self._check_hallucination_risk(output_text, context)
        if hallucination_indicators:
            return SafetyValidation(
                allowed=True,
                risk_level="caution",
                reason=f"Response contains indicators that should be verified: {', '.join(hallucination_indicators[:3])}",
                safe_response=output_text,  # Still allow but flag
                flagged_terms=hallucination_indicators,
                validation_metadata={
                    "check_type": "output_validation",
                    "timestamp": datetime.now().isoformat(),
                    "filter_type": "hallucination_check"
                }
            )

        # Output appears safe
        return SafetyValidation(
            allowed=True,
            risk_level="safe",
            reason="Output passes safety validation",
            safe_response=output_text,
            flagged_terms=[],
            validation_metadata={
                "check_type": "output_validation",
                "timestamp": datetime.now().isoformat(),
                "filter_type": "safe"
            }
        )

    def _check_patterns(self, text: str, patterns: List[str]) -> List[str]:
        """Check text against a list of regex patterns."""
        matches = []
        text_lower = text.lower()

        for pattern in patterns:
            compiled = re.compile(pattern, re.IGNORECASE)
            hits = compiled.findall(text_lower)
            if hits:
                matches.extend([str(hit)[:50] for hit in hits])  # Truncate for logging

        return list(set(matches))  # Remove duplicates

    def _filter_pii(self, text: str) -> SafetyFilterResult:
        """Filter out PII from text with redaction."""
        filtered_text = text
        redaction_reasons = []
        redaction_count = 0

        for pattern, reason in self.PII_PATTERNS:
            compiled = re.compile(pattern, re.IGNORECASE | re.MULTILINE)
            matches = compiled.findall(filtered_text)

            for match in matches:
                filtered_text = filtered_text.replace(match, f"[REDACTED_{reason.upper()}]")
                redaction_reasons.append(f"{reason}: {match[:20]}...")
                redaction_count += 1

        return SafetyFilterResult(
            clear_text=text,
            redacted_content=filtered_text,
            redaction_count=redaction_count,
            redaction_reasons=redaction_reasons
        )

    def _check_hallucination_risk(self, text: str, context: Optional[Dict[str, Any]]) -> List[str]:
        """Check for indicators that response might be hallucinated."""
        indicators = []

        # Check for suspiciously high confidence claims
        if context and context.get("confidence", 0) > 0.95:
            # Only flag if we have conflict markers
            if "KV-wins applied" in text or "conflicts" in text.lower():
                indicators.append("high_confidence_claims")

        # Check for absolute certainty without evidence
        certainty_phrases = ["absolutely certain", "definitely", "without a doubt", "100% sure"]
        for phrase in certainty_phrases:
            if phrase in text.lower() and "canonical" not in text.lower():
                indicators.append(f"certainty_phrase: {phrase}")

        # Check for inconsistent source attribution
        source_markers = ["[KV:", "[Semantic:"]
        source_counts = sum(1 for marker in source_markers if marker in text)

        if source_counts == 0 and len(text) > 100:
            indicators.append("missing_source_attribution")

        # Check for conflicting provenance
        if "KV:" in text and "conflicts" in text.lower():
            if not ("KV-wins" in text or "canonical" in text.lower()):
                indicators.append("unresolved_provenance_conflict")

        return indicators

    def get_safety_stats(self) -> Dict[str, Any]:
        """Get statistics about safety agent performance."""
        return {
            "total_blocked": self.blocked_attempts,
            "caution_triggers": self.caution_triggers,
            "redactions_performed": self.redactions_performed,
            "uptime_seconds": 0,  # Could track this
            "patterns_checked": len(self.BLOCK_PATTERNS + self.CAUTION_PATTERNS),
            "pii_patterns": len(self.PII_PATTERNS)
        }

    def health_check(self) -> bool:
        """Check if safety agent is operational."""
        try:
            # Test input validation
            result = self.validate_input("What is my name?")
            return result.allowed == True and result.risk_level in ["safe", "caution"]

        except Exception:
            return False
