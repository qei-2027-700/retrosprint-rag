# ドキュメント

現行の配置方針は [リポジトリ構成](architecture/repository-layout.md) を正本とする。採用した構成と、実装・動作検証済みの範囲は区別する。

[開発方針と完了条件](project-plan.md) に最終要件、ETL連携・認可・削除の条件、未決事項と残作業をまとめる。Issue #1から移した現行方針であり、`planning/` の初期検討記録とは区別する。個別作業は独立したIssueで管理する。

| 配置 | 内容 |
| --- | --- |
| `specs/` | 機能の期待動作・権限・受入条件。仕様化する際に追加 |
| [architecture/](architecture/repository-layout.md) | 共通設計とリポジトリ配置 |
| [adr/](adr/README.md) | 重要な判断の選択肢・採用理由・変更履歴 |
| `planning/` | 2026年10月12日の初期検討記録 |

## 初期検討記録

以下の3文書は履歴として保存する。仮称、配置、技術の選定状態などに現在と異なる記述がある。目的・採用技術・開発状況は [ルートREADME](../README.md)、現在の配置は [リポジトリ構成](architecture/repository-layout.md) を参照する。

- [実行計画](planning/rag-portfolio-plan.md)
- [詳細設計](planning/rag-portfolio-design.md)
- [レビュー記録](planning/rag-portfolio-review.md)

既存の認可・削除・非同期・費用制御・ETL連携の検討条件は維持する。履歴を移したことだけで実装要件が不要になったり、実装・検証が完了したりすることはない。

## AI開発の共通設定

[開発ルール](rules/development.md) をCodexとClaude Codeで共有する。`AGENTS.md` はこの文書を読む指示を持ち、`CLAUDE.md` は同じ文書をimportする。リポジトリ固有のskillはまだなく、共有用ディレクトリと探索用リンクは追加時に作る。

## 仕様・API・DBの設計順序

アプリのDBは [PostgreSQL](adr/0006-postgresql.md) を採用する。配置先・ORM・テーブル構造は未決定。

1. `specs/` で機能ごとの利用者・権限・正常動作・状態・エラー・削除範囲・受入条件を決める。
2. `architecture/api.md` でAPIの操作・認可・エラー・非同期処理の共通方針を整理する。実装後のHTTP形式はFastAPIから生成するOpenAPIを参照する。
3. `architecture/data-model.md` でPostgreSQLのテーブル・関連・制約・所有者・削除・トランザクションを設計する。

API方針とデータモデルの文書は設計時に追加する。実装は小さな機能単位で進め、仕様・API・DB間で必要な見直しを行う。

## 画面設計

[フロントエンドの画面とコンポーネント](architecture/frontend-layout.md) に、最初の疎通確認画面のPC・スマホレイアウト、状態表示、コンポーネント構成、確認条件と、後続の業務画面の方向性を記載する。
