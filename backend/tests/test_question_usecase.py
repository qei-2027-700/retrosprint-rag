"""Exercise orchestration without FastAPI, HTTP models, or fake adapters."""

from unittest.mock import Mock

import pytest

from retrosprint_rag.application.ports import Generation, ProcessingFailed, Search
from retrosprint_rag.application.questions import AskQuestion
from retrosprint_rag.domain.models import Answer, Citation


def test_no_evidence_skips_generation() -> None:
    search = Mock(spec=Search)
    search.search.return_value = []
    generation = Mock(spec=Generation)
    result = AskQuestion(search, generation).execute("question without evidence")
    assert result.answer is None
    assert result.citations == []
    search.search.assert_called_once_with("question without evidence")
    generation.generate.assert_not_called()


def test_generation_uses_retrieved_evidence() -> None:
    citation = Citation(
        id="source-42",
        document_id="independent-document",
        document_name="Independent document",
        content_version="v2",
        reflection_month="2026-10",
        heading="Notes",
        quote="Evidence",
        original_text="Evidence in context",
    )
    answer = Answer(text="A different answer", citation_ids=[citation.id])
    search = Mock(spec=Search)
    search.search.return_value = [citation]
    generation = Mock(spec=Generation)
    generation.generate.return_value = answer
    result = AskQuestion(search, generation).execute("a different question")
    generation.generate.assert_called_once_with("a different question", [citation])
    assert result.answer == answer
    assert result.citations == [citation]


@pytest.mark.parametrize("failing_port", ["search", "generation"])
def test_processing_failure_propagates_without_http_translation(failing_port: str) -> None:
    search = Mock(spec=Search)
    search.search.return_value = [Mock(spec=Citation)]
    generation = Mock(spec=Generation)
    getattr(
        search if failing_port == "search" else generation,
        failing_port if failing_port == "search" else "generate",
    ).side_effect = ProcessingFailed
    with pytest.raises(ProcessingFailed):
        AskQuestion(search, generation).execute("question")
