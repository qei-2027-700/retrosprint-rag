"""Retrieve full month documents or related evidence, then validate generation."""

from dataclasses import dataclass

from retrosprint_rag.application.ports import Generation, GenerationFailed, MonthDocuments, Search
from retrosprint_rag.domain.models import Answer, Citation, Coverage, RetrievalMode, Status


@dataclass(frozen=True)
class QuestionResult:
    status: Status
    answer: Answer | None
    citations: list[Citation]
    coverage: Coverage
    message: str | None = None


class AskQuestion:
    def __init__(self, search: Search, generation: Generation, months: MonthDocuments) -> None:
        self._search = search
        self._generation = generation
        self._months = months

    def execute(
        self,
        question: str,
        retrieval_mode: RetrievalMode = "related_search",
        reflection_month: str | None = None,
    ) -> QuestionResult:
        monthly = retrieval_mode == "monthly_reflection"
        if monthly and reflection_month is None:
            raise ValueError("Month required")
        evidence = (
            self._months.fetch_month(reflection_month or "")
            if monthly
            else self._search.search(question, reflection_month)
        )
        documents = evidence.documents
        # Conservative fake input budget: one Unicode code point per token, including metadata.
        input_size = (
            len(question)
            + 1000
            + sum(len(d.content) + len(d.document_id) + len(d.content_version) for d in documents)
        )
        exceeded = (
            len(documents) > 50
            or sum(len(d.content.encode("utf-8")) for d in documents) > 1024 * 1024
            or input_size > 20000
        )
        omitted = evidence.omitted or exceeded
        coverage = Coverage(
            scope="month_documents" if monthly else "search_matches",
            complete=monthly and bool(documents) and not omitted,
            omitted=omitted,
            documents_retrieved=len(documents),
            documents_used=0,
            checked_at=evidence.checked_at,
        )

        def empty(status: Status, message: str) -> QuestionResult:
            return QuestionResult(status, None, [], coverage, message)

        if omitted:
            return empty(
                "input_limit_exceeded",
                "全文を処理できません。取得件数は確認できた件数の下限です。対象を見直してください。",
            )
        if not documents:
            if monthly:
                return empty(
                    "no_documents", "対象月の文書がありません。対象月を変えてお試しください。"
                )
            if evidence.stale:
                return empty(
                    "stale_evidence", "旧版の資料だけが見つかりました。同期を待ってお試しください。"
                )
            return empty(
                "insufficient_evidence",
                "回答の根拠となる資料が見つかりませんでした。質問を変えてお試しください。",
            )
        coverage = Coverage(
            coverage.scope,
            coverage.complete,
            omitted,
            len(documents),
            len(documents),
            evidence.checked_at,
        )
        by_document = {(d.document_id, d.content_version): d for d in documents}
        ids = [c.id for c in evidence.citations]
        for c in evidence.citations:
            document = by_document.get((c.document_id, c.content_version))
            if (
                document is None
                or c.locator.start < 0
                or c.locator.end <= c.locator.start
                or document.content[c.locator.start : c.locator.end] != c.quote
                or c.reflection_month != document.reflection_month
                or c.original_text != document.content
            ):
                raise GenerationFailed
        if len(ids) != len(set(ids)):
            raise GenerationFailed
        answer = self._generation.generate(question, evidence, coverage)
        if answer is None:
            return empty(
                "insufficient_evidence",
                "取得した資料では質問に答える根拠が不足しています。質問を変えてお試しください。",
            )
        if (
            not answer.text.strip()
            or not answer.citation_ids
            or not set(answer.citation_ids) <= set(ids)
        ):
            raise GenerationFailed
        return QuestionResult("answered", answer, evidence.citations, coverage)
