"""Deterministic local adapters using synthetic reflection text."""

from retrosprint_rag.application.ports import ProcessingFailed
from retrosprint_rag.domain.models import Answer, Citation

SAMPLE_TEXT = (
    "2026年9月の振り返り（合成資料）\n\n"
    "うまくいったこと\n"
    "作業を小さく分けたら、着手しやすくなった。\n"
    "次の日に取り組む作業を前日に一つ決めておいた。\n\n"
    "次に試すこと\n週末に進み具合を振り返る。"
)


class FakeSearch:
    def search(self, question: str) -> list[Citation]:
        if question == "処理失敗の確認":
            raise ProcessingFailed
        if question != "最近うまくいったことは？":
            return []
        return [
            Citation(
                id="c1",
                document_id="reflection-2026-09",
                document_name="2026年9月の振り返り（合成資料）",
                content_version="v1",
                reflection_month="2026-09",
                heading="うまくいったこと",
                quote="作業を小さく分けたら、着手しやすくなった。",
                original_text=SAMPLE_TEXT,
            )
        ]


class FakeGeneration:
    def generate(self, question: str, citations: list[Citation]) -> Answer:
        return Answer(
            text="作業を小さく分けることで、着手しやすくなっています。",
            citation_ids=[citation.id for citation in citations],
        )
