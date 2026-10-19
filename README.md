# retrosprint-rag

本人の直近の振り返りから経験・悩み・成果を整理し、これからの私生活や行動方針を考えるための対話アプリ。記録を検索し、根拠・出典を確認しながら複数ターンの対話を行う。

`go-drive-etl` が取得・加工・ロードした振り返り文書を活用し、まずは本人向けに有用性を確かめる。その後、他の利用者への展開を検討する。バックエンドとフロントエンドを含む独立したモノレポとして開発する。

## 現在の状態

2026年10月18日時点で、FastAPIのhealth・開発用echo、Nuxt 4の接続テスト画面、OpenAPIによる型生成、ローカル検証コマンドとGitHub Actions workflowを実装している。業務機能、DB・AWS接続、CDK・デプロイは未実装。PR #3の[GitHub Actions](https://github.com/qei-2027-700/retrosprint-rag/actions/runs/39138159089)で通常CIの成功を確認済み。

本READMEは、[開発計画 Issue #1](https://github.com/qei-2027-700/retrosprint-rag/issues/1) の最新方針と既存の3文書をまとめた入口となる。既存文書に残る仮称 `rag-portfolio`、バックエンド選定、期限については、本READMEとIssue #1に記載した更新後の方針を参照する。ディレクトリ構成は、その後の検討を反映した [配置方針](docs/architecture/repository-layout.md) に従う。アプリのDBはPostgreSQLを採用する。DBの配置先やAPIの実行基盤は引き続き検討対象とする。

## 目指す使い方

1. 振り返り文書を取り込み、年月や出典を保持する。
2. 「最近うまくいったことは何か」「同じ悩みを繰り返していないか」などを質問する。
3. 回答の引用箇所と原文を確認し、追加質問で経験や今後の行動を整理する。
4. 保存した会話を再表示し、後日も対話を続ける。

根拠が不足する場合は、その旨を返す。年月を指定した全体の振り返りと、類似検索で一部の根拠を探す質問は別の処理として設計する。

## 技術方針

| 対象 | 採用済みの技術・方針 |
| --- | --- |
| フロントエンド | Nuxt 4、TypeScript、Tailwind CSS系 |
| バックエンド | Python、FastAPI |
| アプリのDB | PostgreSQL。配置先・ORM・テーブル設計は未決定 |
| インフラ | AWS先行、AWS CDK / TypeScript |
| 回答生成・embedding | Amazon Bedrock |
| ベクトル保存・類似検索 | Amazon S3 Vectors |
| 認証 | Amazon Cognito |
| ETL成果物 | BigQueryの `etl_gold.reflection_documents` を利用する計画 |

バックエンドはrepositoryのinterfaceと具体実装を分離する。内部の詳細構造は未確定とする。業務層にAWS SDK、認証claim、BigQueryクライアントの具体型を持ち込まない。

アプリのDBは [PostgreSQLを採用する](docs/adr/0006-postgresql.md)。旧設計のDynamoDB固有の保存・配送方式は見直す。Lambda、SQS、CloudFrontによる静的配信、非同期ジョブとポーリングは既存設計の構成案。リージョン、生成・embeddingモデル、次元数、予算・利用枠、公開方法の詳細と合わせて、検証後にADRへ判断を残す。

LangChainはBedrock接続と文書分割に限定して使う案がある。LangGraphは分岐・反復などが必要になった段階、LangSmithは評価段階での任意採用とし、初期の必須条件には含めない。

## 全体構成

以下は責務と接続先を示す計画図であり、稼働中の構成図ではない。

```text
go-drive-etl（取得・加工・ロード）
  └─ BigQuery: etl_gold.reflection_documents
       └─ ETL連携adapter（直接参照 / AWS取り込み / 用途別併用を検討）
            │
ブラウザ ─ Nuxt 4 ─ FastAPI（認証・認可、文書・会話API）
             │       ├─ 文書取り込み・検索・回答のusecase / worker
          Cognito    │    ├─ S3：原文・抽出本文の保存案
                     │    ├─ Bedrock：embedding・回答生成
                     │    └─ S3 Vectors：ベクトル保存・類似検索
                     └─ PostgreSQL：文書状態・会話履歴・ジョブ等（テーブル設計は未確定）
```

### ETLとの連携

`etl_gold.reflection_documents` の文書単位の最新本文と、`file_id`、`document_name`、`drive_url`、`content_version`、`reflection_month`、取り込み日時などを利用する。集計表やCSVを文書本文の代わりにはしない。

| 接続案 | 検討する内容 |
| --- | --- |
| BigQuery直接参照 | AWSバックエンドからパラメータ付きSQLで対象月・文書を取得する。実行基盤からのGoogle Cloud認証・接続を検証する |
| AWS側へ取り込み | 認可された本文をS3へ取り込み、Bedrock embeddingとS3 Vectorsへ接続する。原文のID・版・出典を保持する |
| 用途別に併用 | 月全体の取得と類似検索など、用途に応じて使い分ける |

方式は未決定。認証、更新・再取り込み・削除、重複、出典、越境転送、費用を比較し、データ契約とともにADRで決める。サンプル文書によるAWS RAGの構成検証と、ETL連携の設計は並行して進められる。

年月指定には `reflection_month = @month` を使い、取り込み日や推測した開始・終了日で代用しない。月全体の要約には対象文書全体を取得する処理が必要で、top-k検索だけで網羅したとは扱わない。入力上限などで全文を扱えなければ、省略を明示する。

Issue #1の2026年10月16日の記録では、ETL側のGold View作成と専用サービスアカウントによる月検索確認は完了している。AWSアプリ実行基盤からの認証・接続は未検証。正確な対象期間の重複検索は [go-drive-etl Issue #133](https://github.com/qei-2027-700/go-drive-etl/issues/133) で扱う。

## 最終的な必須機能

以下は実装予定であり、実装済み機能の一覧ではない。

| 機能 | 完成時の動作 |
| --- | --- |
| 認証・ロール分離 | Cognitoでログインし、管理者（`admin`）と通常ユーザー（`user`）の権限を画面・APIの両方で制御する |
| ファイルアップロード | 初期は管理者がMarkdown・テキスト・テキスト抽出可能なPDFを登録し、取り込み状態・失敗理由を確認する |
| 根拠付き回答 | 文書を検索し、回答と文書名・ページまたは見出し・引用箇所を示す。根拠不足も扱う |
| 複数ターンの会話・履歴 | 追加質問、会話一覧、再表示・継続・削除を行う。他ユーザーの会話へのアクセスを拒否する |
| 文書管理 | 文書一覧、カテゴリ絞り込み、原文表示、管理者による再試行・削除を行う |

初期対象外は、音声、OCR、Office文書、エージェント、複数embeddingモデル。ストリーミングや一般チャットは追加候補とする。

## 個人データと公開デモ

本人の私的記録は、本人だけが読める利用から始める。公開デモは招待制を基本案とし、認証・認可を備え、共有文書には公開可能な自作の合成データを使う。勤務先の内部情報や私的記録、認証情報を公開資料へ含めない。

初期デモでは管理者が共有資料を登録し、通常ユーザーは質問・引用確認・自分の会話履歴を利用する。管理者であっても他ユーザーの会話を閲覧・変更できない設計とする。共有サンプル文書のモデルだけで個人文書の分離ができるとは扱わず、他の利用者へ展開する前に、文書・会話・出典の利用者ごとの分離を設計・検証する。

既存設計の削除方針では、文書削除時に新規検索・原文URL発行を停止し、保存先から非同期に削除する。発行済み原文URLには最大2分の有効期間があり、保存済みチャット本文に含まれる引用文の除去や、監査・バックアップからの即時消去は含めない。会話削除も論理的な利用停止と非同期削除を分ける。これらは実装・検証前の仕様であり、採用構成に合わせて確定する。

## 開発の段階

### 2026年10月末の中間デモ

10月末はETL / BIをポートフォリオとして仕上げる。RAGアプリは全機能完成を月末の条件にせず、約40%を目安に処理と構成を示せる中間デモを目指す。40%は現在の達成率や測定済みの工数比率ではない。

中間デモでは、公開可能なサンプルの「検索 → 回答 → 出典確認」と、画面またはAPIによる代表操作を示す。構成図でETL・検索・回答・画面の担当を説明し、実AWSで確認済みの部分、fake、未実装を区別する。具体的な範囲は実装Issueへの分割時に確定する。

ログイン、権限分離、アップロード、会話履歴などの最終要件は維持する。個人文書を使う公開デモは認証・アクセス制限の確認を前提とし、11月の転職活動中も残りの開発を継続する。

### 次の作業

1. モノレポの雛形、ADR、開発用の `AGENTS.md`、再現可能な起動・検証手順を整え、成果単位の実装Issueに分割する。
2. ETL連携の候補を比較し、データ契約・認証・更新と削除・費用・中間デモの範囲を決める。
3. サンプル1文書でBedrock embedding → S3 Vectors検索 → 根拠付き回答を検証し、実AWSとfakeの結果を分けて記録する。
4. 認証・権限、アップロードと取り込み、複数ターンの会話・履歴を実装し、採用したETL連携を実行基盤から確認する。
5. CI、固定評価、費用と利用枠、停止・復旧、デモと運用資料を整える。

## ディレクトリ構成

ルート直下に `backend/`、`frontend/`、`infra/`、`docs/` を置く。API型とHTTPクライアントはfrontend内、品質評価はbackend内で管理する。

```text
retrosprint-rag/
├── backend/
│   ├── src/retrosprint_rag/   # 内部の詳細構造は未確定
│   ├── tests/
│   └── evaluations/          # 合成資料・検索や回答の評価・実験結果
├── frontend/
│   ├── app/api/              # 生成型とHTTPクライアント
│   └── openapi/              # FastAPIから出力するOpenAPI
├── infra/                # AWS CDK / TypeScript
└── docs/                     # 仕様・共通設計・ADR・既存の検討記録
```

配置方針の正本は [リポジトリ構成](docs/architecture/repository-layout.md)。バックエンドはrepositoryのinterfaceと具体実装を分離する方針とする。内部のディレクトリ名・ファイル名・分割単位は未確定で、実装時に決める。

この方針で従来の `apps/`・`packages/api-client/`・ルートの `evals/` 案を置き換える。図は実装時の配置を示すもので、実装済みの一覧ではない。

## 起動・検証

[mise](https://mise.jdx.dev/getting-started.html) を導入してから、リポジトリのルートで次の手順を実行する。CIではmise 2026.3.7を使う。シェルのactivate設定は必須ではなく、`mise run` と `mise exec -- <コマンド>` から固定したツールを利用できる。

ツールのバージョンと共通コマンドはルートの `mise.toml` で管理する。Node 24.22.0、Python 3.13.5、pnpm 10.34.7、uv 0.8.15を使い、ツールの配布元とチェックサムは `mise.lock`、ライブラリ依存は `frontend/pnpm-lock.yaml` と `backend/uv.lock` に固定する。

```sh
mise trust mise.toml
mise install --locked
mise run setup
cp -n backend/.env.example backend/.env
cp -n frontend/.env.example frontend/.env
```

共通タスクとツールのバージョンはmiseで管理する。FEは `frontend/package.json` と `frontend/pnpm-lock.yaml`、BEは `backend/pyproject.toml` と `backend/uv.lock` で依存を管理する。現在はpnpm workspaceを使わず、ルートにpackage manifestやpnpmの設定・lockfileを置かない。

別々のターミナルで `mise run dev:be` と `mise run dev:fe` を実行し、`http://localhost:3000` を開く。echoはbackendの環境設定で有効化する。APIは `http://localhost:8000`。設定と詳細手順は [Backend](backend/README.md)・[Frontend](frontend/README.md)、期待動作は [接続テスト仕様](docs/specs/dev-connectivity.md) を参照する。

検証時は開発サーバーを停止して3000・8000番ポートを空ける。

```sh
mise run browser:install
mkdir -p .logs
mise run check > .logs/check.log 2>&1
```

`mise run check` はBEのlint・型・契約テスト・配布物ビルドと導入、FEの型・単体テスト・静的生成、OpenAPIと型の再生成差分、実HTTPのE2Eを実行する。個別には `mise run check:be`、`mise run check:fe`、`mise run api:generate`、`mise run api:check`、`mise run test:e2e` を使う。生成物を変更した場合はコミットしてから差分チェックを実行する。

GitHub ActionsはmainへのpushとPRで同じ `mise run check` を実行する。通常CIはDB・AWS・認証情報を使わない。CDK synthやAWSデプロイは対象外。[CI採用ADR](docs/adr/0005-github-actions-ci.md) と [型生成ADR](docs/adr/0007-openapi-client.md) を参照する。

2026年10月18日、mise導入前にNode 24.22.0・Python 3.13.5のローカル環境で、新しいcheckoutに対するlockfileからの依存導入と `pnpm check` が成功した。BEの契約テスト14件、FEの単体テスト1件、静的生成物から実APIに接続するE2E 8件を含む。型不一致、API契約変更後の型エラー・生成差分、未追跡の生成ファイル、APIテスト失敗も意図的な変更で検出を確認し、検証用の変更は復元した。

この検証のログは `.logs/check-be.log`、`.logs/check-fe.log`、`.logs/api-check.log`、`.logs/fresh-check.log`、`.logs/negative-checks.log` に保存した。E2Eのスクリーンショットと失敗時traceの出力先は `frontend/test-results/`。CIではログとE2E出力を `validation-results` artifactに7日間保存する。ログと画面画像はGit管理しない。2026年10月19日の確認時点で、Nuxt 5互換設定を含むコミット `de2a4e8` の[GitHub Actions](https://github.com/qei-2027-700/retrosprint-rag/actions/runs/39138159089)も成功している。実機のキーボード・縦横表示・スクリーンリーダーは未確認。

RAGは検索のRecall@k、引用の整合性、根拠への忠実性、回答不能の正しさを固定評価で確認する。認可拒否、入力上限、重複・再試行、削除競合、履歴再開も検証する。評価値・応答時間・費用は測定条件とともに記録し、設計上の目標や見積もりを実績として扱わない。

## 関連資料

| 資料 | 内容 |
| --- | --- |
| [実行計画](docs/planning/rag-portfolio-plan.md) | 2026年10月12日の採用候補、実装順序、評価・運用の計画 |
| [詳細設計](docs/planning/rag-portfolio-design.md) | API、保存方式、状態遷移、認証・認可、削除、障害回復、公開前の検証条件 |
| [レビュー記録](docs/planning/rag-portfolio-review.md) | 設計への指摘、反映内容、実装時に残る判断・検証 |
| [開発計画 Issue #1](https://github.com/qei-2027-700/retrosprint-rag/issues/1) | 正式名・採用技術・ETL連携・中間デモに関する更新後の方針とETL側の追跡 |

3文書は設計時点の記録として参照する。設計への反映と実装検証の完了を区別し、実装時の重要な判断・変更・検証結果はADRへ残す。
