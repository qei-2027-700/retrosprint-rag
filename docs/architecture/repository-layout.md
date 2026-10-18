# リポジトリ構成

決定日：2026年10月18日。状態：全体の配置方針は採用済み、実装前。backendの詳細構造は未確定。

本書をディレクトリ配置方針の正本とする。FastAPI / Python、Nuxt 4 SPA、AWS CDK / TypeScriptのモノレポとして、ルート直下に `backend/`、`frontend/`、`infra/`、`docs/` を置く。

## 採用理由

アプリがフロントエンドとバックエンド各1つのため、ルート直下で管理する。TypeScriptのAPI利用先はNuxtだけなので、型生成とHTTPクライアントはfrontendに含める。品質評価はPythonの検索usecaseを使うためbackendに含め、独立したPythonプロジェクトにはしない。

従来の `apps/`、`packages/api-client/`、ルートの `evals/`・`configs/rag/` の配置案は本書で置き換える。複数のアプリで共有する必要が生じた場合は、共有パッケージへの切り出しを改めて判断する。

## 全体構成

以下は配置先を示す設計図。すべての空ディレクトリを先に作ることはせず、実装に必要なものから追加する。各層の内部は少数のファイルから始め、ディレクトリを増やすのは、同じ責務のファイルが増えて見通しが悪くなった時点とする。

```text
retrosprint-rag/
├── backend/
│   ├── pyproject.toml
│   ├── uv.lock
│   ├── src/retrosprint_rag/
│   │   ├── …                     # 内部のファイル・ディレクトリ構成は未確定
│   │   └── resources/
│   │       ├── prompts/
│   │       └── rag/
│   ├── scripts/export_openapi.py
│   ├── tests/
│   │   ├── unit/
│   │   ├── contract/
│   │   └── integration/
│   └── evaluations/
│       ├── README.md
│       ├── run_retrieval.py
│       ├── metrics.py
│       ├── configs/
│       ├── datasets/reflection_v1/
│       │   ├── README.md
│       │   ├── corpus/
│       │   ├── manifest.json
│       │   ├── development.jsonl
│       │   └── test.jsonl
│       └── results/
├── frontend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── generated/schema.d.ts
│   │   │   └── client.ts
│   │   ├── pages/
│   │   ├── components/
│   │   ├── composables/
│   │   ├── middleware/
│   │   └── layouts/
│   ├── openapi/openapi.json
│   ├── public/
│   ├── tests/
│   ├── nuxt.config.ts
│   └── package.json
├── infra/aws/
│   ├── bin/
│   ├── lib/
│   │   ├── stacks/
│   │   └── constructs/
│   ├── test/
│   ├── cdk.json
│   └── package.json
├── docs/
│   ├── README.md
│   ├── specs/
│   ├── architecture/
│   │   └── repository-layout.md
│   ├── adr/
│   ├── rules/                    # Codex・Claude Code共通の規則
│   ├── skills/                   # 共通skillの実体
│   └── planning/                 # 既存3文書を過去の検討記録として保持
├── .github/workflows/
├── .gitignore
├── .env.example
├── AGENTS.md                    # 共通ルールを読む入口
├── CLAUDE.md                    # 同じ共通ルールをimport
├── README.md
├── package.json
├── pnpm-workspace.yaml
└── pnpm-lock.yaml
```

`docs/planning/` は既存資料を保持するための例外。新しい仕様・設計は `specs/`、`architecture/`、`adr/` に記載する。AI開発の共通ルールは `rules/`、共通skillの実体は `skills/` に置く。旧資料は現行の配置方針の正本にはしない。

アプリのDBは [PostgreSQLを採用する](../adr/0006-postgresql.md)。配置先・ORM・テーブル構造、APIの実行基盤、キュー配送、ETL接続方式は未決定。具体adapterは選定した方式に合わせて追加する。

## バックエンドの分離方針

backendの詳細構造は未確定とする。現時点で決めるのは、repositoryのinterface（契約）と具体実装を分離し、利用側はinterfaceを通して呼び出すこと。ディレクトリ名、ファイル名、分割単位、層別構成は実装時に決める。

これまで挙げた `models.py`、`interfaces.py`、`repositories/`、`services/`、`api.py`、`workers.py`、`bootstrap.py` は配置案であり、採用済みの構造として扱わない。細かな層分けや空ディレクトリの先行作成は求めない。

認可・削除・非同期・費用制御等の既存要件は維持する。内部構造を未確定とすることで、それらの要件が不要になるわけではない。

### Pythonパッケージ

`src/retrosprint_rag/` を一つの名前空間とし、API・worker・評価から `retrosprint_rag` をimportする。通常パッケージとして必要な `__init__.py` を配置する。

`pyproject.toml` でbuild backendとsrcレイアウトのパッケージ検出を設定する。backendをインストールした環境で実行し、`sys.path` の手動変更や実行ディレクトリへの依存を避ける。promptsと標準RAG設定は配布物に同梱し、`importlib.resources` 等で参照する。

## フロントエンドとAPI契約

初期は `ssr: false` のNuxt SPAとする。画面上の認証誘導・表示制御に加えて、API側でも認証・認可を行う。

```text
FastAPIのAPI定義・Pydantic schemas
  → frontend/openapi/openapi.json
  → frontend/app/api/generated/schema.d.ts
  → frontend/app/api/client.ts・composablesで利用
```

OpenAPIとTypeScript型は生成物としてGit管理し、手編集しない。CIで再生成差分を確認する。API定義の出力はAWS接続・実際の認証情報なしで実行できるようにする。

`client.ts` は接続先、認証情報の付与、共通エラー処理を実装する。内部DTOやDB型は直接公開しない。型生成・HTTPクライアントのツールと版は導入時に固定する。SSEを追加する場合は、イベントの型と受信時の検証を別途設計する。

## 標準設定と品質評価

標準の分割・検索設定は `backend/src/retrosprint_rag/resources/rag/`、prompt本文は `resources/prompts/` を正本とする。評価の `configs/` は標準設定を参照し、実験で変える項目だけを指定する。

| 配置 | 内容 |
| --- | --- |
| `backend/tests/` | 仕様、認可、状態遷移、エラー処理、契約、評価指標の計算などの検証 |
| `backend/evaluations/` | 検索順位・回答品質・遅延・費用の測定コードと実行方法 |
| `evaluations/datasets/` | 合成文書、文書ID・版の対応、質問、正解根拠 |
| `evaluations/configs/` | baselineなどの実験条件 |
| `evaluations/results/` | 生の結果、解決後の全設定、比較・失敗例。原則Git対象外 |

評価はアプリ本体の検索usecaseを呼び、検索ロジックを複製しない。調整用の `development.jsonl` と固定の `test.jsonl` を分ける。正解根拠は文書ID・版・根拠箇所で保持し、分割設定を変えて比較できるようにする。

結果にはコード・dataset・promptの版、モデル・次元、解決後の全設定、指標と測定条件を記録する。共有する小さな比較報告が必要になったら `evaluations/reports/` を追加し、条件・指標・失敗例をGit管理する。私的記録、アップロード実資料、embeddingベクトル、認証情報はGitへ追加しない。評価の資料・indexは運用中のものと分ける。

## 文書の正本

| 情報 | 配置 |
| --- | --- |
| アプリの目的・利用者・範囲・開発状況 | ルート `README.md` |
| 文書の案内 | `docs/README.md` |
| 機能の期待動作・権限・エラー・受入条件・未決事項 | `docs/specs/` |
| 共通の構造・状態・配送契約・配置 | `docs/architecture/` |
| 重要な選択肢・採用理由・変更の経緯 | `docs/adr/` |
| HTTP形式 | FastAPIのAPI定義・Pydantic schemas |
| 標準RAG設定・prompt・評価データ | backend内の各正本 |
| 作業・実装と検証の結果 | Issue・PR・CI |

specsは利用者ができることで分類する。ログイン・ログアウト、チャット回答、資料取り込み、会話履歴、退会などを単位とし、分割・embedding・検索を個別の機能仕様フォルダにはしない。退会を仕様化する際は削除範囲、保持期間、処理中・失敗時の扱いを定義し、未決事項を推測で埋めない。退会の月末版への収録は未確定。

必要な機能だけ技術詳細の `design.md` を追加する。共通の契約はarchitectureを参照し、APIフィールド一覧や設定値を重複して手書きしない。ADRは重要な判断ごとに記録し、変更時は旧判断への参照と現行仕様の更新を行う。

起動・型生成手順は各アプリやinfraのREADME、評価手順は `backend/evaluations/README.md` に必要に応じて置く。独立した運用文書群や仕様の空ファイルは初期作成の要件にしない。

## 導入時の確認

1. backendをインストールし、API・worker・評価から同じ名前でimportできることを確認する。配布物にはpromptと標準RAG設定を含める。
2. repositoryの利用側がinterface経由で呼び出すことと、認可・状態の確認が必要な処理に適用されることを確認する。
3. AWS接続なしでOpenAPI・型生成を実行し、再生成差分をCIで検出できることを確認する。
4. アプリと評価が同じ検索usecase・標準設定を使い、評価結果を測定条件とともに保存できることを確認する。
5. 実装した部分、fakeによる検証、実AWSで確認した範囲を区別する。配置方針の採用を機能完成とは扱わない。

本書は [z-private-kanri Issue #13](https://github.com/qei-2027-700/z-private-kanri/issues/13) の配置・文書管理方針と、本リポジトリでの検討を反映している。元Issueの私的な記録は転載しない。

## CodexとClaude Codeの共通設定

共通ルールは [開発ルール](../rules/development.md) にまとめ、ルートの `AGENTS.md` と `CLAUDE.md` から参照する。skillは `docs/skills/` に置き、`.agents/skills → ../docs/skills`、`.claude/skills → ../docs/skills` の相対シンボリックリンクで共有する。配置と確認方法は [共通skill](../skills/README.md) を参照する。
