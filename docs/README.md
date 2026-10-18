# ドキュメント

現行の配置方針は [リポジトリ構成](architecture/repository-layout.md) を正本とする。採用した構成と、実装・動作検証済みの範囲は区別する。

| 配置 | 内容 |
| --- | --- |
| `specs/` | 機能の期待動作・権限・受入条件。仕様化する際に追加 |
| [architecture/](architecture/repository-layout.md) | 共通設計とリポジトリ配置 |
| `adr/` | 重要な判断の選択肢・採用理由・変更履歴。判断を記録する際に追加 |
| `planning/` | 2026年10月12日の初期検討記録 |

## 初期検討記録

以下の3文書は履歴として保存する。仮称、配置、技術の選定状態などに現在と異なる記述がある。目的・採用技術・開発状況は [ルートREADME](../README.md)、現在の配置は [リポジトリ構成](architecture/repository-layout.md) を参照する。

- [実行計画](planning/rag-portfolio-plan.md)
- [詳細設計](planning/rag-portfolio-design.md)
- [レビュー記録](planning/rag-portfolio-review.md)

既存の認可・削除・非同期・費用制御・ETL連携の検討条件は維持する。履歴を移したことだけで実装要件が不要になったり、実装・検証が完了したりすることはない。
