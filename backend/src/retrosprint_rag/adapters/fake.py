"""Deterministic synthetic documents; no external services."""

from datetime import UTC, datetime

from retrosprint_rag.application.ports import ProcessingFailed, RetrievalFailed
from retrosprint_rag.domain.models import Answer, Citation, Coverage, Document, Evidence, Locator

SAMPLE_TEXT = (
    "2026年9月の振り返り（合成資料）\n\n"
    "うまくいったこと\n"
    "作業を小さく分けたら、着手しやすくなった。\n"
    "次の日に取り組む作業を前日に一つ決めておいた。\n\n"
    "次に試すこと\n週末に進み具合を振り返る。"
)
SECOND_TEXT = (
    "2026年9月の相談記録（合成資料）\n悩み\n"
    "相談を後回しにして、一人で抱え込んだ。\n次に試すこと\n翌朝に相談する。"
)
DOCUMENTS = [
    Document("reflection-2026-09", "v1", "2026-09", "2026年9月の振り返り（合成資料）", SAMPLE_TEXT),
    Document(
        "consultation-2026-09", "v2", "2026-09", "2026年9月の相談記録（合成資料）", SECOND_TEXT
    ),
    Document(
        "reflection-2026-10",
        "v1",
        "2026-10",
        "2026年10月の相談記録（合成資料）",
        "悩み\n早めの相談で手戻りを減らせた。",
    ),
]


def make_evidence(documents: list[Document], *, stale: bool = False) -> Evidence:
    citations = []
    for i, d in enumerate(documents):
        quote = (
            d.content.splitlines()[3]
            if d.document_id == "reflection-2026-09"
            else (
                d.content.splitlines()[2]
                if d.document_id == "consultation-2026-09"
                else d.content.splitlines()[-1]
            )
        )
        start = d.content.index(quote)
        citations.append(
            Citation(
                f"c{i + 1}",
                d.document_id,
                d.document_name,
                d.content_version,
                d.reflection_month,
                "うまくいったこと" if i == 0 and d.document_id == "reflection-2026-09" else None,
                quote,
                d.content,
                Locator(start, start + len(quote)),
            )
        )
    return Evidence(documents, citations, datetime.now(UTC).isoformat(), stale=stale)


class FakeMonthDocuments:
    def fetch_month(self, reflection_month: str) -> Evidence:
        if reflection_month == "2026-06":
            raise RetrievalFailed
        if reflection_month == "2026-08":
            return make_evidence(
                [
                    Document(f"limit-{i}", "v1", reflection_month, "上限確認", "合成資料")
                    for i in range(51)
                ]
            )
        return make_evidence([d for d in DOCUMENTS if d.reflection_month == reflection_month])


class FakeSearch:
    def search(self, question: str, reflection_month: str | None = None) -> Evidence:
        if question == "処理失敗の確認":
            raise ProcessingFailed
        if question == "取得失敗の確認":
            raise RetrievalFailed
        if question == "旧版のみの確認":
            return make_evidence([], stale=True)
        documents = []
        if question == "最近うまくいったことは？":
            documents = DOCUMENTS[:1]
        if question == "相談のタイミングで悩んだ経験は？":
            documents = DOCUMENTS[1:]
        return make_evidence(
            [
                d
                for d in documents
                if reflection_month is None or d.reflection_month == reflection_month
            ]
        )


class FakeGeneration:
    def generate(self, question: str, evidence: Evidence, coverage: Coverage) -> Answer | None:
        if question == "処理失敗の確認":
            raise ProcessingFailed
        if question not in {
            "最近うまくいったことは？",
            "この月の成果と悩みを整理して",
            "相談のタイミングで悩んだ経験は？",
        }:
            return None
        text = (
            "作業を小さく分けることで、着手しやすくなっています。"
            if question == "最近うまくいったことは？"
            else "資料にある成果・悩みと次に試すことを確認できます。"
        )
        if question != "最近うまくいったことは？" or not any(
            d.document_id == "reflection-2026-09" for d in evidence.documents
        ):
            text = "\n".join(f"{c.quote} [{c.id}]" for c in evidence.citations)
        return Answer(text, [c.id for c in evidence.citations])
