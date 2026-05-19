"""Tests for memoryhub.extraction.extractors.relationship.RelationshipExtractor."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from memoryhub.extraction.extractors.relationship import RelationshipExtractor
from memoryhub.extraction.models import CandidateMemory, TraceEvent
from memoryhub.models import Memory, SearchResult


@pytest.mark.asyncio
class TestRelationshipExtractor:
    """Test RelationshipExtractor functionality."""

    def _make_memory(
        self,
        memory_id: str,
        content: str,
        relevance_score: float = 0.8,
    ) -> Memory:
        """Create a mock Memory object for search results."""
        return Memory(
            id=memory_id,
            content=content,
            relevance_score=relevance_score,
            scope="user",
            weight=0.7,
            is_current=True,
        )

    def _make_candidate(self, content: str = "Test preference") -> CandidateMemory:
        """Create a simple candidate memory."""
        return CandidateMemory(
            content=content,
            scope="user",
            weight=0.7,
            confidence=0.7,
            source_event=TraceEvent.user_message("test"),
            extractor_name="test",
        )

    async def test_extract_returns_empty_list_always(self) -> None:
        """extract() always returns empty list."""
        extractor = RelationshipExtractor()
        event = TraceEvent.user_message("I prefer FastAPI")

        candidates = await extractor.extract(event)

        assert len(candidates) == 0

    async def test_enrich_adds_related_memory_ids(self) -> None:
        """enrich() adds related memory IDs from search results."""
        # Mock client with search results
        mock_client = MagicMock()
        search_result = SearchResult(
            results=[],
            total_matching=2,
            has_more=False,
        )
        # Add raw dict results for the relationship extractor to process
        search_result.results = [
            self._make_memory("mem-001", "FastAPI is fast", relevance_score=0.75),
            self._make_memory("mem-002", "FastAPI tutorial", relevance_score=0.68),
        ]
        mock_client.search = AsyncMock(return_value=search_result)

        extractor = RelationshipExtractor()
        candidate = self._make_candidate("I prefer FastAPI over Flask")

        enriched = await extractor.enrich(candidate, mock_client)

        assert len(enriched.relate_to) == 2
        assert "mem-001" in enriched.relate_to
        assert "mem-002" in enriched.relate_to

    async def test_enrich_respects_relevance_threshold(self) -> None:
        """enrich() respects relevance_threshold, excluding low-relevance results."""
        mock_client = MagicMock()
        search_result = SearchResult(
            results=[
                self._make_memory("mem-001", "FastAPI", relevance_score=0.75),
                self._make_memory("mem-002", "Django", relevance_score=0.45),  # Below threshold
            ],
            total_matching=2,
            has_more=False,
        )
        mock_client.search = AsyncMock(return_value=search_result)

        extractor = RelationshipExtractor(relevance_threshold=0.6)
        candidate = self._make_candidate()

        enriched = await extractor.enrich(candidate, mock_client)

        # Only mem-001 should be included (0.75 >= 0.6)
        assert len(enriched.relate_to) == 1
        assert "mem-001" in enriched.relate_to
        assert "mem-002" not in enriched.relate_to

    async def test_enrich_caps_at_max_relations(self) -> None:
        """enrich() caps related memories at max_relations."""
        mock_client = MagicMock()
        search_result = SearchResult(
            results=[
                self._make_memory("mem-001", "Memory 1", relevance_score=0.9),
                self._make_memory("mem-002", "Memory 2", relevance_score=0.85),
                self._make_memory("mem-003", "Memory 3", relevance_score=0.8),
                self._make_memory("mem-004", "Memory 4", relevance_score=0.75),
            ],
            total_matching=4,
            has_more=False,
        )
        mock_client.search = AsyncMock(return_value=search_result)

        extractor = RelationshipExtractor(max_relations=2)
        candidate = self._make_candidate()

        enriched = await extractor.enrich(candidate, mock_client)

        # Should cap at 2 relations
        assert len(enriched.relate_to) == 2

    async def test_enrich_sets_parent_for_high_relevance(self) -> None:
        """enrich() sets parent_id for very high relevance matches (>0.85)."""
        mock_client = MagicMock()
        search_result = SearchResult(
            results=[
                self._make_memory("mem-001", "Exact match", relevance_score=0.92),
                self._make_memory("mem-002", "Related", relevance_score=0.7),
            ],
            total_matching=2,
            has_more=False,
        )
        mock_client.search = AsyncMock(return_value=search_result)

        extractor = RelationshipExtractor()
        candidate = self._make_candidate()

        enriched = await extractor.enrich(candidate, mock_client)

        # Very high match should become parent
        assert enriched.parent_id == "mem-001"
        # Both should still be in relate_to
        assert len(enriched.relate_to) == 2

    async def test_enrich_does_not_override_existing_parent(self) -> None:
        """enrich() does not override an existing parent_id."""
        mock_client = MagicMock()
        search_result = SearchResult(
            results=[
                self._make_memory("mem-001", "High match", relevance_score=0.92),
            ],
            total_matching=1,
            has_more=False,
        )
        mock_client.search = AsyncMock(return_value=search_result)

        extractor = RelationshipExtractor()
        candidate = self._make_candidate()
        candidate.parent_id = "existing-parent"

        enriched = await extractor.enrich(candidate, mock_client)

        # Should not override existing parent
        assert enriched.parent_id == "existing-parent"

    async def test_enrich_handles_search_failure_gracefully(self) -> None:
        """enrich() handles search failure gracefully, returning candidate unchanged."""
        mock_client = MagicMock()
        mock_client.search = AsyncMock(side_effect=Exception("Search failed"))

        extractor = RelationshipExtractor()
        candidate = self._make_candidate()

        enriched = await extractor.enrich(candidate, mock_client)

        # Candidate should be returned unchanged
        assert enriched == candidate
        assert len(enriched.relate_to) == 0

    async def test_name_property_returns_relationship(self) -> None:
        """Name property returns 'relationship'."""
        extractor = RelationshipExtractor()
        assert extractor.name == "relationship"

    async def test_enrich_passes_project_id_to_search(self) -> None:
        """enrich() passes project_id to client.search when provided."""
        mock_client = MagicMock()
        search_result = SearchResult(results=[], total_matching=0, has_more=False)
        mock_client.search = AsyncMock(return_value=search_result)

        extractor = RelationshipExtractor()
        candidate = self._make_candidate()

        await extractor.enrich(candidate, mock_client, project_id="test-project")

        # Verify project_id was passed to search
        mock_client.search.assert_called_once()
        call_kwargs = mock_client.search.call_args.kwargs
        assert call_kwargs.get("project_id") == "test-project"

    async def test_enrich_mutates_candidate_in_place(self) -> None:
        """enrich() mutates the candidate in place and returns it."""
        mock_client = MagicMock()
        search_result = SearchResult(
            results=[
                self._make_memory("mem-001", "Related", relevance_score=0.8),
            ],
            total_matching=1,
            has_more=False,
        )
        mock_client.search = AsyncMock(return_value=search_result)

        extractor = RelationshipExtractor()
        candidate = self._make_candidate()
        original_id = id(candidate)

        enriched = await extractor.enrich(candidate, mock_client)

        # Should return the same object (mutated in place)
        assert id(enriched) == original_id
        assert len(enriched.relate_to) == 1
