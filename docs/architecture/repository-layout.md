# リポジトリ構成

更新日：2026年10月20日。backend・frontendの疎通構成とCI、BEの開発用Composeを実装済み。業務機能、DB・AWS接続、infraは未実装。

本書を現在の配置と今後の配置方針の参照先とする。構成図は現在の管理対象を示す。未実装の配置は後述し、必要な実装が生じたときに追加する。

## 採用理由

アプリがフロントエンドとバックエンド各1つのため、ルート直下で管理する。TypeScriptのAPI利用先はNuxtだけなので、型生成とHTTPクライアントはfrontendに含める。品質評価はPythonの検索usecaseを使うためbackendに含め、独立したPythonプロジェクトにはしない。

従来の `apps/`、`packages/api-client/`、ルートの `evals/`・`configs/rag/` の配置案は本書で置き換える。複数のアプリで共有する必要が生じた場合は、共有パッケージへの切り出しを改めて判断する。

## 現在の構成

主要な管理対象を示す。依存のインストール先・キャッシュ・ビルド出力は省略する。

```text
retrosprint-rag/
├── backend/
│   ├── .env.example
│   ├── Dockerfile
│   ├── .dockerignore
│   ├── README.md
│   ├── pyproject.toml
│   ├── uv.lock
│   ├── src/retrosprint_rag/
│   │   ├── __init__.py
│   │   └── main.py
│   ├── scripts/
│   │   ├── dev.py
│   │   ├── export_openapi.py
│   │   └── check_wheel.py
│   └── tests/test_contract.py
├── frontend/
│   ├── .env.example
│   ├── README.md
│   ├── app/
│   │   ├── app.vue
│   │   ├── api/
│   │   │   ├── client.ts
│   │   │   └── generated/schema.d.ts
│   │   ├── assets/css/main.css
│   │   ├── components/
│   │   ├── composables/
│   │   ├── layouts/
│   │   └── pages/
│   ├── openapi/openapi.json
│   ├── tests/
│   │   ├── connectivity.test.ts
│   │   ├── contract.typecheck.ts
│   │   ├── tsconfig.json
│   │   └── e2e/connectivity.spec.ts
│   ├── nuxt.config.ts
│   ├── tsconfig.json
│   ├── vitest.config.ts
│   ├── playwright.config.ts
│   ├── package.json
│   └── pnpm-lock.yaml
├── docs/
│   ├── README.md
│   ├── specs/
│   ├── architecture/
│   ├── adr/
│   ├── rules/
│   └── planning/
├── scripts/check-generated.mjs
├── .github/workflows/ci.yml
├── .gitignore
├── AGENTS.md
├── CLAUDE.md
├── README.md
├── mise.toml
├── mise.lock
└── compose.yaml             # BEのローカル開発用
```

`mise.toml` はツールのバージョンと共通タスク、`mise.lock` はツール配布物を固定する。pnpmの依存定義・lockfile・install許可設定はFE内、uvの依存定義・lockfileはBE内で管理する。現在はpnpm workspaceを使わず、ルートの `package.json` やpnpmの設定・lockfileは不要。

`infra/`、評価コード、RAG設定・prompt、FEのmiddlewareは未実装で、構成図には含めない。AWS CDKはinfra、検索・回答品質の評価はbackendに置く方針とし、詳細なファイル分割は導入時に決める。

`docs/planning/` は過去の検討記録を保持する。現行の仕様・設計は `specs/`、`architecture/`、`adr/`、AI開発の共通ルールは `rules/` に記載する。旧資料の構成図を現在の配置として扱わない。

アプリのDBは [PostgreSQLを採用する](../adr/0006-postgresql.md)。配置先・ORM・テーブル構造、APIの実行基盤、キュー配送、ETL接続方式は未決定。具体adapterは選定した方式に合わせて追加する。

## バックエンドの分離方針

backendはhandler・usecase・interface・domain・adapterを分離する。[ADR-0011](../adr/0011-backend-layers.md) に依存方向と判断を記載する。repositoryや外部サービスの利用側はinterface（契約）を通して呼び出す。

現在の配置は以下とする。HTTPモデルとdomainの型を分け、内部型をそのままHTTP契約として公開しない。

```text
backend/src/retrosprint_rag/
├── main.py                     # 設定・依存の組み立て・router登録
├── api/
│   ├── questions.py            # 質問のAPIRouter・handler・HTTP変換
│   ├── schemas.py              # 質問のHTTP入力・出力モデル
│   └── connectivity.py         # health・開発用echoのrouterとhandler
├── application/
│   ├── questions.py            # 質問usecase・処理結果
│   └── ports.py                # 検索・回答生成のinterfaceと処理失敗
├── domain/models.py            # 引用・生成回答の業務データ
└── adapters/fake.py            # fake実装と合成資料
```

`api` は `application` を呼び、`application` はinterfaceとdomainだけに依存する。`adapters` はそのinterfaceを実装する。`domain` は標準ライブラリだけで定義し、HTTP・FastAPI・Pydantic・具体adapterを参照しない。`main.py` で具体adapterを選び、usecaseへ注入してrouterを登録する。

DB・AWS・worker等の詳細構造は導入時に決める。未使用の基底クラスや空の配置を先行作成しない。

認可・削除・非同期・費用制御等の既存要件は維持し、各機能の導入時に層間の責務を具体化する。

### Pythonパッケージ

`src/retrosprint_rag/` を一つの名前空間とする。現在はAPIが使い、将来のworker・評価でも `retrosprint_rag` をimportする。通常パッケージとして必要な `__init__.py` を配置する。

`pyproject.toml` でbuild backendとsrcレイアウトのパッケージ検出を設定する。backendをインストールした環境で実行し、`sys.path` の手動変更や実行ディレクトリへの依存を避ける。promptと標準RAG設定を導入するときは配布物に同梱し、`importlib.resources` 等で参照する。

## フロントエンドとAPI契約

初期は `ssr: false` のNuxt SPAとする。認証・認可は未実装。導入時には画面上の表示制御に加えてAPI側でも検証する。

```text
FastAPIのAPI定義・Pydantic schemas
  → frontend/openapi/openapi.json
  → frontend/app/api/generated/schema.d.ts
  → frontend/app/api/client.ts・composablesで利用
```

OpenAPIとTypeScript型は生成物としてGit管理し、手編集しない。CIで再生成差分を確認する。API定義の出力はAWS接続・実際の認証情報なしで実行できるようにする。

現在の `client.ts` は接続先と生成型を使うHTTPクライアントを定義し、疎通の状態・エラーはcomposableで扱う。認証情報の付与は認証の導入時に追加する。内部DTOやDB型は直接公開しない。型生成・HTTPクライアントの版はFEの依存定義とlockfileで固定する。SSEを追加する場合は、イベントの型と受信時の検証を別途設計する。

## 今後の標準設定と品質評価

以下は未実装の方針。具体的な配置・ファイル分割は実装時に確定し、空の雛形は先に作らない。

標準の分割・検索設定とprompt本文はbackendのパッケージに同梱する。評価コード・合成資料・実験条件もbackend内で管理し、標準設定を参照して実験で変える項目だけを指定する。測定の生結果は原則Git対象外とする。

評価はアプリ本体の検索usecaseを呼び、検索ロジックを複製しない。調整用の `development.jsonl` と固定の `test.jsonl` を分ける。正解根拠は文書ID・版・根拠箇所で保持し、分割設定を変えて比較できるようにする。

結果にはコード・dataset・promptの版、モデル・次元、解決後の全設定、指標と測定条件を記録する。共有する小さな比較報告が必要になったら、条件・指標・失敗例をGit管理する。私的記録、アップロード実資料、embeddingベクトル、認証情報はGitへ追加しない。評価の資料・indexは運用中のものと分ける。

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

現在の起動・型生成手順は各アプリのREADMEに置く。infraや評価の手順書は、それぞれの実装時に追加する。独立した運用文書群や仕様の空ファイルは初期作成の要件にしない。

## 業務機能・評価を導入するときの確認

1. backendをインストールし、API・worker・評価から同じ名前でimportできることを確認する。配布物にはpromptと標準RAG設定を含める。
2. repositoryの利用側がinterface経由で呼び出すことと、認可・状態の確認が必要な処理に適用されることを確認する。
3. AWS接続なしでOpenAPI・型生成を実行し、再生成差分をCIで検出できることを確認する。
4. アプリと評価が同じ検索usecase・標準設定を使い、評価結果を測定条件とともに保存できることを確認する。
5. 実装した部分、fakeによる検証、実AWSで確認した範囲を区別する。配置方針の採用を機能完成とは扱わない。

本書は [z-private-kanri Issue #13](https://github.com/qei-2027-700/z-private-kanri/issues/13) の配置・文書管理方針と、本リポジトリでの検討を反映している。元Issueの私的な記録は転載しない。

## CodexとClaude Codeの共通設定

共通ルールは [開発ルール](../rules/development.md) にまとめ、ルートの `AGENTS.md` と `CLAUDE.md` から参照する。現在はリポジトリ固有のskillを持たない。共有skill用のディレクトリと探索用リンクは、実際にskillを追加するときに作る。個人環境の `evid-verify`・`gh-attach` はリポジトリにコピーしない。
