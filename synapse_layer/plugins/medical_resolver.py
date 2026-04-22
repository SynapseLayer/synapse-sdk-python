"""
Synapse Layer — Medical Truth Resolver Plugin
Domain-specific plugin for validating and resolving medical/clinical memories.
"""

from typing import List
from synapse_layer.plugins.base import (
    MemoryResolverPlugin,
    MemoryCandidate,
    ResolverDecision,
)

# Source priority for medical facts
SOURCE_PRIORITY = {
    "peer_reviewed": 5,      # Highest: Published peer-reviewed medical literature
    "clinical_guideline": 4,  # Clinical practice guidelines from organizations
    "specialist_note": 3,    # Notes from a medical specialist
    "general_knowledge": 2,  # General medical knowledge bases
    "patient_report": 1,     # Patient self-reported information (lowest)
}


class MedicalTruthResolver(MemoryResolverPlugin):
    """Validates and resolves conflicts in medical/clinical memories.
    
    Uses a priority-based system to determine which source of medical
    information is most reliable when conflicts occur.
    """
    
    @property
    def name(self) -> str:
        """Return plugin identifier."""
        return "medical_truth"
    
    def can_handle(self, candidates: List[MemoryCandidate]) -> bool:
        """Check if candidates contain medical/clinical information.
        
        A simple heuristic: check if metadata contains 'medical', 'clinical',
        'diagnosis', 'treatment', or 'symptom' tags.
        
        Args:
            candidates: List of memory candidates
            
        Returns:
            True if at least one candidate has medical metadata
        """
        medical_keywords = {
            "medical", "clinical", "diagnosis", "treatment",
            "symptom", "disease", "condition", "medication",
            "prescription", "health", "patient"
        }
        
        for candidate in candidates:
            # Check metadata tags
            tags = candidate.metadata.get("tags", [])
            if any(kw in str(tags).lower() for kw in medical_keywords):
                return True
            
            # Check content keywords
            content_lower = candidate.content.lower()
            if any(kw in content_lower for kw in medical_keywords):
                return True
        
        return False
    
    def resolve(self, candidates: List[MemoryCandidate]) -> ResolverDecision:
        """Resolve medical truth conflicts using source priority and relevance.
        
        Algorithm:
        1. Extract source priority from metadata
        2. If sources differ, highest priority wins
        3. If same source, most recent wins
        4. Consider relevance score as secondary factor
        
        Args:
            candidates: List of memory candidates
            
        Returns:
            ResolverDecision indicating the winner and reasoning
        """
        if not candidates:
            return ResolverDecision(
                reasoning="No candidates to resolve",
                action="reject",
                confidence=1.0,
            )
        
        if len(candidates) == 1:
            return ResolverDecision(
                winner_memory_id=candidates[0].memory_id,
                reasoning="Single candidate, no conflict",
                action="accept",
                confidence=1.0,
            )
        
        # Score each candidate
        scored = []
        for candidate in candidates:
            source = candidate.metadata.get("source_type", "general_knowledge")
            priority = SOURCE_PRIORITY.get(source, 0)
            
            # Combined score: (priority * 100) + relevance score
            combined_score = (priority * 100) + candidate.relevance_score
            scored.append((combined_score, candidate))
        
        # Sort by score (descending)
        scored.sort(key=lambda x: x[0], reverse=True)
        winner_score, winner_candidate = scored[0]
        
        # Losers become deprecated
        deprecated_ids = [c[1].memory_id for c in scored[1:]]
        
        # Build reasoning
        winner_source = winner_candidate.metadata.get("source_type", "general_knowledge")
        reasoning = (
            f"Medical truth resolved: {winner_source} (priority={SOURCE_PRIORITY.get(winner_source, 0)}) "
            f"wins over {len(deprecated_ids)} other candidate(s). "
            f"Winner relevance: {winner_candidate.relevance_score:.2f}"
        )
        
        return ResolverDecision(
            winner_memory_id=winner_candidate.memory_id,
            reasoning=reasoning,
            confidence=0.95 if len(deprecated_ids) == 1 else 0.85,
            action="accept",
            deprecated_ids=deprecated_ids,
        )
    
    def on_load(self) -> None:
        """Called when plugin is registered."""
        # Could initialize medical terminology lookup, etc.
        pass
    
    def on_unload(self) -> None:
        """Called when plugin is unregistered."""
        # Could clean up resources
        pass
