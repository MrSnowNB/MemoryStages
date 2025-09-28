"""
Stage 7.2 MVP - Memory Adapter
Privacy-enforcing gateway between agents and canonical memory.

NO agent can bypass this adapter to access memory directly.
All memory access must go through this privacy gatekeeper.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import re
import json
from ..core import dao
from ..core.config import debug_enabled


class MemoryAdapter:
    """
    Privacy-enforcing gateway between agents and canonical memory.
    NO agent can bypass this adapter to access memory directly.
    All responses must be validated against canonical memory.
    """

    def __init__(self):
        self.access_log = []
        self.validation_cache = {}
        self.sensitive_patterns = [
            r'\b\d{3}-\d{2}-\d{4}\b',  # SSN pattern
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email pattern
            r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b',  # Credit card pattern
            r'\b\d{10,}\b',  # Long numbers (could be sensitive IDs)
        ]
        self.sensitive_keywords = [
            'password', 'secret', 'private key', 'confidential',
            'social security', 'ssn', 'credit card', 'bank account',
            'authentication', 'login credentials'
        ]

    def get_validation_context(self, query: str, user_id: str = None,
                             max_results: int = 3) -> List[Dict[str, Any]]:
        """
        Get memory context for response validation.
        Applies strict privacy and tombstone filtering.
        Only returns safe, vetted memory content for the specified user.

        Args:
            query: User query to find relevant context
            user_id: User identifier for privacy filtering (required for user scoping)
            max_results: Maximum number of context results to return

        Returns:
            List of safe memory context items for validation
        """
        try:
            # Ensure user_id is provided and valid
            if not user_id or not user_id.strip():
                user_id = "default"

            # Log memory access attempt (audit trail)
            self._log_memory_access("validation_context", query, user_id)

            # Try vector search first (Stage 2 feature)
            context_results = []
            vector_available = self._is_vector_search_available()

            if vector_available:
                try:
                    context_results = self._get_vector_context(query, user_id, max_results)
                except Exception as e:
                    # Log vector search failure but continue with fallback
                    self._log_memory_access("vector_search_failed", query, user_id, error=str(e))

            # If vector search failed or unavailable, use fallback
            if not context_results:
                context_results = self._get_fallback_context_new(query, user_id, max_results)

            # Apply final safety filtering
            safe_context = []
            for ctx in context_results:
                if self._is_safe_for_context(ctx):
                    safe_context.append({
                        'content': ctx.get('content', ''),
                        'source': ctx.get('source', 'memory'),
                        'updated_at': ctx.get('updated_at', datetime.now().isoformat()),
                        'key': ctx.get('key', ''),
                        'relevance_score': ctx.get('relevance_score', 0.0),
                        'sensitive': ctx.get('sensitive', False),
                        'user_id': user_id  # Include user_id in context
                    })

            # Limit to max_results and sort by relevance
            safe_context.sort(key=lambda x: x.get('relevance_score', 0.0), reverse=True)
            safe_context = safe_context[:max_results]

            # Log successful context retrieval
            self._log_memory_access("context_retrieved", query, user_id,
                                  results_count=len(safe_context))

            return safe_context

        except Exception as e:
            # Log error and return empty context for safety
            self._log_memory_access("context_error", query, user_id, error=str(e))
            return []

    def validate_facts_in_response(self, response: str, user_id: str = "default",
                                 memory_context: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Validate that factual claims in response are supported by memory.
        Returns validation results with detailed analysis.

        Args:
            response: The response text to validate
            memory_context: Memory context to validate against

        Returns:
            Dict with validation results and metadata
        """
        if not memory_context:
            return {
                'validated': False,
                'reason': 'no_memory_context',
                'facts_found': 0,
                'facts_validated': 0
            }

        # Extract potential facts from response
        response_facts = self._extract_facts_from_response(response)

        if not response_facts:
            # No factual claims found - consider this valid
            return {
                'validated': True,
                'reason': 'no_factual_claims',
                'facts_found': 0,
                'facts_validated': 0
            }

        # Validate each fact against memory context
        validated_count = 0
        validation_details = []

        for fact in response_facts:
            fact_valid = self._fact_supported_by_memory(fact, memory_context)
            validation_details.append({
                'fact': fact[:100],  # Truncate for logging
                'validated': fact_valid,
                'confidence': self._calculate_fact_confidence(fact, memory_context)
            })
            if fact_valid:
                validated_count += 1

        # Require at least 70% of facts to be validated for MVP
        validation_threshold = 0.7
        validation_ratio = validated_count / len(response_facts) if response_facts else 1.0
        is_validated = validation_ratio >= validation_threshold

        result = {
            'validated': is_validated,
            'reason': 'fact_validation_' + ('passed' if is_validated else 'failed'),
            'facts_found': len(response_facts),
            'facts_validated': validated_count,
            'validation_ratio': validation_ratio,
            'validation_details': validation_details
        }

        # Log validation attempt
        dao.add_event(
            actor="memory_adapter",
            action="fact_validation",
            payload=json.dumps({
                "response_length": len(response),
                "facts_found": len(response_facts),
                "facts_validated": validated_count,
                "validation_ratio": validation_ratio,
                "validation_passed": is_validated
            })
        )

        return result

    def contains_sensitive_data(self, text: str) -> Dict[str, Any]:
        """
        Check if text contains sensitive data patterns.
        Prevents sensitive data leakage in responses.

        Args:
            text: Text to scan for sensitive data

        Returns:
            Dict with detection results and detected patterns
        """
        detected_patterns = []
        text_lower = text.lower()

        # Check regex patterns
        for pattern in self.sensitive_patterns:
            matches = re.findall(pattern, text)
            if matches:
                detected_patterns.extend([{'type': 'regex_pattern', 'value': match} for match in matches])

        # Check sensitive keywords
        for keyword in self.sensitive_keywords:
            if keyword in text_lower:
                detected_patterns.append({'type': 'sensitive_keyword', 'value': keyword})

        is_sensitive = len(detected_patterns) > 0

        # Log sensitive data detection if found
        if is_sensitive:
            dao.add_event(
                actor="memory_adapter",
                action="sensitive_data_detected",
                payload=json.dumps({
                    "text_length": len(text),
                    "patterns_detected": len(detected_patterns),
                    "pattern_types": list(set([p['type'] for p in detected_patterns]))
                })
            )

        return {
            'contains_sensitive': is_sensitive,
            'detected_patterns': detected_patterns,
            'text_length': len(text)
        }

    def _get_vector_context(self, query: str, user_id: str, max_results: int) -> List[Dict[str, Any]]:
        """Get context using vector search (Stage 2 feature)."""
        if not self._is_vector_search_available():
            return []

        try:
            # Use Stage 2 semantic search if available
            from ..core.search_service import semantic_search
            search_results = semantic_search(query=query, top_k=max_results)

            context_results = []
            for result in search_results:
                # Convert Stage 2 format to our context format
                if self._is_safe_for_context(result):
                    context_results.append({
                        'content': result.get('value', ''),
                        'source': 'vector_search',
                        'updated_at': result.get('updated_at', datetime.now().isoformat()),
                        'key': result.get('key', ''),
                        'relevance_score': result.get('score', 0.0),
                        'sensitive': result.get('sensitive', False)
                    })

            return context_results

        except ImportError:
            # Stage 2 not available
            return []
        except Exception as e:
            # Log but don't fail - return empty for fallback
            return []

    def _get_fallback_context_new(self, query: str, user_id: str, max_results: int) -> List[Dict[str, Any]]:
        """Query-aware KV context: prioritizes user-relevant keys for validation."""
        try:
            # Get keys for the specific user
            all_keys = dao.list_keys(user_id)
            relevant_context = []

            query_words = set(query.lower().split()) if query else set()

            # FIRST: PRIORITIZE USER-RELEVANT KEYS based on query content
            prioritized_keys = []
            query_lower = query.lower()

            # Identity and profile keys get highest priority
            if 'displayName' in query_lower or 'display name' in query_lower or 'name' in query_lower.replace(' ', ''):
                prioritized_keys.append('displayName')
            if 'age' in query_lower:
                prioritized_keys.append('age')
            if any(term in query_lower for term in ['favorite color', 'favoriteColor', 'colour', 'color']):
                prioritized_keys.append('favoriteColor')
            if any(term in query_lower for term in ['location', 'where', 'city']):
                prioritized_keys.append('location')

            # Fetch prioritized keys from KV and add to context
            seen_keys = set()
            for priority_key in prioritized_keys:
                if priority_key in seen_keys:
                    continue
                try:
                    kv_record = dao.get_key(user_id, priority_key)
                    if kv_record and kv_record.value and self._is_safe_for_context(kv_record):
                        relevant_context.append({
                            'content': kv_record.value,
                            'source': 'kv_priority',
                            'updated_at': kv_record.updated_at.isoformat() if kv_record.updated_at else datetime.now().isoformat(),
                            'key': kv_record.key,
                            'relevance_score': 1.0,  # Highest priority for validation
                            'sensitive': kv_record.sensitive,
                            'user_id': user_id
                        })
                        seen_keys.add(priority_key)
                except Exception:
                    continue  # Skip if key doesn't exist or other error

            # SECOND: Add recent non-sensitive keys for broader context
            for kv_item in all_keys[:min(50, len(all_keys))]:
                # Skip if already added or not safe
                if kv_item.key in seen_keys or not self._is_safe_for_context(kv_item):
                    continue

                if not kv_item.value or not kv_item.value.strip():
                    continue

                # Calculate relevance based on content overlap
                value_words = set(kv_item.value.lower().split())
                overlap = len(query_words & value_words) if query_words else 0

                relevance_score = len(query_words) > 0 and overlap / len(query_words) or 0.1

                # Include if reasonably relevant or we have few results
                if relevance_score > 0.1 or len(relevant_context) < max_results // 2:
                    relevant_context.append({
                        'content': kv_item.value,
                        'source': 'kv_fallback',
                        'updated_at': kv_item.updated_at.isoformat() if kv_item.updated_at else datetime.now().isoformat(),
                        'key': kv_item.key,
                        'relevance_score': relevance_score,
                        'sensitive': kv_item.sensitive,
                        'user_id': user_id
                    })
                    seen_keys.add(kv_item.key)

            return relevant_context

        except Exception as e:
            # Log error but return empty for safety
            return []

    def _is_safe_for_context(self, memory_item: Dict[str, Any]) -> bool:
        """Check if memory item is safe to include in context."""
        # Skip sensitive data
        if memory_item.get('sensitive', False):
            return False

        # Skip empty/tombstone entries
        content = memory_item.get('value', memory_item.get('content', ''))
        if not content or not content.strip():
            return False

        # Check for sensitive patterns in content
        sensitive_check = self.contains_sensitive_data(content)
        if sensitive_check['contains_sensitive']:
            return False

        return True

    def _is_vector_search_available(self) -> bool:
        """Check if vector search functionality is available."""
        try:
            # Check if Stage 2 modules exist
            from ..core.search_service import semantic_search
            from ..core.config import are_vector_features_enabled
            return are_vector_features_enabled()
        except ImportError:
            return False

    def _extract_facts_from_response(self, response: str) -> List[str]:
        """Extract potential factual statements from response."""
        # Split into sentences
        sentences = re.split(r'[.!?]+', response)

        facts = []
        fact_indicators = ['is', 'are', 'was', 'were', 'has', 'have', 'will', 'can']

        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 8:  # Skip very short sentences
                # Check if sentence contains factual indicators
                words = sentence.lower().split()
                if any(indicator in words for indicator in fact_indicators):
                    facts.append(sentence)

        return facts

    def _fact_supported_by_memory(self, fact: str, memory_context: List[Dict[str, Any]]) -> bool:
        """Check if a fact is supported by memory context."""
        fact_words = set(fact.lower().split())

        for ctx in memory_context:
            content = ctx.get('content', '').lower()
            # Skip empty context
            if not content.strip():
                continue

            content_words = set(content.split())

            # Check for significant word overlap
            overlap = len(fact_words & content_words)
            if overlap >= min(3, len(fact_words) // 2):
                return True

        return False

    def _calculate_fact_confidence(self, fact: str, memory_context: List[Dict[str, Any]]) -> float:
        """Calculate confidence score for fact validation."""
        if not memory_context:
            return 0.0

        max_overlap = 0
        fact_words = set(fact.lower().split())

        for ctx in memory_context:
            content = ctx.get('content', '').lower()
            if not content.strip():
                continue

            content_words = set(content.split())
            overlap = len(fact_words & content_words)

            if overlap > max_overlap:
                max_overlap = overlap

        # Normalize by fact length
        confidence = min(max_overlap / len(fact_words), 1.0) if fact_words else 0.0
        return confidence

    def _log_memory_access(self, operation: str, query: str, user_id: str = None,
                          results_count: int = 0, error: str = None):
        """Log memory access for comprehensive audit trail."""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'operation': operation,
            'query_length': len(query) if query else 0,
            'user_id': user_id,
            'results_count': results_count,
            'success': error is None,
            'error': error
        }

        self.access_log.append(log_entry)

        # Also log to persistent episodic system
        dao.add_event(
            actor="memory_adapter",
            action=f"memory_{operation}",
            payload=json.dumps(log_entry)
        )

    def get_access_stats(self) -> Dict[str, Any]:
        """Get memory access statistics for monitoring."""
        if not self.access_log:
            return {'total_accesses': 0, 'error_rate': 0.0, 'recent_errors': []}

        total = len(self.access_log)
        errors = [e for e in self.access_log if e.get('error')]
        recent_errors = errors[-5:] if errors else []  # Last 5 errors

        return {
            'total_accesses': total,
            'error_rate': len(errors) / total if total > 0 else 0.0,
            'recent_errors': recent_errors,
            'last_access': self.access_log[-1] if self.access_log else None
        }
