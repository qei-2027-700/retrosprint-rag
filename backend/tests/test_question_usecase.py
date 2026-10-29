"""Test orchestration and citation integrity independently of HTTP."""

from dataclasses import replace
from unittest.mock import Mock

import pytest

from retrosprint_rag.adapters.fake import (
    DOCUMENTS,
    FakeGeneration,
    FakeMonthDocuments,
    FakeSearch,
    make_evidence,
)
from retrosprint_rag.application.ports import (
    Generation,
    GenerationFailed,
    MonthDocuments,
    RetrievalFailed,
    Search,
)
from retrosprint_rag.application.questions import AskQuestion
from retrosprint_rag.domain.models import Answer, Document, Locator


def test_month_full_text_goes_to_generation_without_search() -> None:
    search = Mock(spec=Search)
    months = Mock(spec=MonthDocuments)
    evidence = make_evidence(DOCUMENTS[:2])
    months.fetch_month.return_value = evidence
    generation = Mock(spec=Generation)
    generation.generate.return_value = Answer("Both documents", ["c1", "c2"])
    result = AskQuestion(search, generation, months).execute(
        "summary", "monthly_reflection", "2026-09"
    )
    search.search.assert_not_called()
    months.fetch_month.assert_called_once_with("2026-09")
    generation.generate.assert_called_once_with("summary", evidence, result.coverage)
    assert [d.content for d in evidence.documents] == [d.content for d in DOCUMENTS[:2]]
    assert result.coverage.complete
    assert result.coverage.documents_used == 2
    assert result.coverage.documents_retrieved == 2
    for c in result.citations:
        d = next(d for d in evidence.documents if d.document_id == c.document_id)
        assert c.content_version == d.content_version
        assert d.content[c.locator.start : c.locator.end] == c.quote


@pytest.mark.parametrize("kind", ["documents", "bytes", "tokens"])
def test_limit_skips_generation(kind: str) -> None:
    documents = [
        Document("large", "v1", "2026-09", None, "x" * (1048577 if kind == "bytes" else 20001))
    ]
    if kind == "documents":
        documents = [Document(str(i), "v1", "2026-09", None, "data") for i in range(51)]
    months = Mock(spec=MonthDocuments)
    months.fetch_month.return_value = make_evidence(documents)
    generation = Mock(spec=Generation)
    result = AskQuestion(Mock(spec=Search), generation, months).execute(
        "summary", "monthly_reflection", "2026-09"
    )
    generation.generate.assert_not_called()
    assert result.status == "input_limit_exceeded"
    assert result.coverage.omitted and not result.coverage.complete
    assert result.coverage.documents_used == 0


def test_empty_month_and_retrieval_failure_skip_generation() -> None:
    generation = Mock(spec=Generation)
    usecase = AskQuestion(FakeSearch(), generation, FakeMonthDocuments())
    assert usecase.execute("summary", "monthly_reflection", "2025-01").status == "no_documents"
    with pytest.raises(RetrievalFailed):
        usecase.execute("summary", "monthly_reflection", "2026-06")
    generation.generate.assert_not_called()


@pytest.mark.parametrize("corruption", ["version", "locator", "answer"])
def test_invalid_citation_is_generation_failure(corruption: str) -> None:
    evidence = make_evidence(DOCUMENTS[:1])
    c = evidence.citations[0]
    if corruption == "version":
        evidence = replace(evidence, citations=[replace(c, content_version="wrong")])
    if corruption == "locator":
        evidence = replace(evidence, citations=[replace(c, locator=Locator(0, 1))])
    search = Mock(spec=Search)
    search.search.return_value = evidence
    generation = Mock(spec=Generation)
    generation.generate.return_value = Answer(
        "answer", ["unknown"] if corruption == "answer" else ["c1"]
    )
    with pytest.raises(GenerationFailed):
        AskQuestion(search, generation, FakeMonthDocuments()).execute("question")


def test_search_month_filter_and_non_completeness() -> None:
    usecase = AskQuestion(FakeSearch(), FakeGeneration(), FakeMonthDocuments())
    result = usecase.execute("相談のタイミングで悩んだ経験は？", reflection_month="2026-10")
    assert result.status == "answered"
    assert not result.coverage.complete
    assert [c.reflection_month for c in result.citations] == ["2026-10"]
    assert usecase.execute("旧版のみの確認").status == "stale_evidence"
    assert usecase.execute("unknown").status == "insufficient_evidence"
