# RAGポートフォリオ実行計画

作成日：2026-10-12。リポジトリ名は `rag-portfolio` を仮置きする。

詳細なAPI・保存方式・状態遷移・セキュリティ・検証条件は [設計書](rag-portfolio-design.md)、レビュー結果と残る判断事項は [レビュー記録](rag-portfolio-review.md) にまとめる。本書は実行順序と採用方針を扱う。AWSリソースやリポジトリはまだ作成していない。

## 確定条件と着手時に決めること

| 区分 | 内容 |
| --- | --- |
| 必須技術・構成 | Nuxt 4、Tailwind CSS系、モノレポ、AWS CDK、Bedrock、S3 Vectors、Cognito |
| 必須機能 | ファイルアップロード、複数ターンのチャット、会話履歴、管理者と通常ユーザーのロール分離 |
| 推奨する実装案 | FastAPI、LangChainの一部、Lambda、DynamoDB、非同期ジョブとポーリング |
| 公開方法の初期案 | 招待制、公開可能な共有資料、管理者のみアップロード、TOTPによるMFA、保持期間の設定 |
| 着手時の決定・検証 | repo名、バックエンド・基盤・DB、リージョン、モデル・次元数・依存の版、月額予算と利用枠 |

必須条件は維持する。推奨案と初期値は段階1でADRに記録し、実アカウントの対応状況・費用・検証結果から確定する。検証済みと未検証を区別し、コードや環境がない段階で公開可能とは判断しない。

## 方針

Nuxt 4・Tailwind CSS 4・FastAPI・LangChainの一部コンポーネント・AWS CDK（TypeScript）のモノレポを第一候補とする。文書の登録、検索、根拠付き回答までを完成させ、RAGの評価結果と設計判断を公開する。

Amazon BedrockとAmazon S3 Vectorsの利用は必須条件とする。文書・質問のembeddingと回答生成はBedrock、ベクトル保存と類似検索はS3 Vectorsを使う。バックエンド言語と実行基盤を変更する場合も、この条件は維持する。

ファイルアップロード機能・チャット機能・Amazon Cognitoによる認証も必須条件とする。アップロードから検索可能になるまでの処理と、会話の継続・履歴の保存までをMVPに含める。

ユーザーのロールは管理者（`admin`）と通常ユーザー（`user`）の2つに分ける。権限は画面の表示とAPIの両方で制御する。

SAFを参考にする範囲は、文書管理とRAGチャットという機能、バックエンドの責務分離、AWSサービスとの接続とする。実装は公開資料と自作の架空文書を使って独立して作る。公開READMEには勤務先の内部構成・コード・データを含めない。

公開デモの固定費を抑えることを仮の優先条件とする。バックエンドはLambda、履歴・文書メタデータはDynamoDBから始める。ECS・PostgreSQLの運用経験を示すことが主目的なら、着手前にECS Fargate・RDS PostgreSQLへ切り替える。どちらもバックエンドの層分けは共通にする。

## バックエンド選定

| 観点 | FastAPI / Python | Go |
| --- | --- | --- |
| 今回の適性 | 文書処理とRAGの試行を同じ言語で進められる | AWS SDKを使うRAGは実装可能。API設計や並行処理を示しやすい |
| API契約 | 型定義からOpenAPIを出力できる | OpenAPIの定義・生成方法を別途決める |
| 学習・実績 | Python・RAGの習熟を主目的にする場合の第一候補 | Goバックエンドの求人に向けた作品を優先する場合の第一候補 |
| 注意点 | 型チェック、同期SDK呼び出し、依存関係を管理する | PDF処理や評価ツールの選定が必要。別言語追加は運用を増やす |

暫定採用はFastAPI。初期段階でGo APIとPythonワーカーを併設しない。Python案ではLangChainのBedrock接続・文書分割コンポーネントを採用し、S3 VectorsはAWS SDKで操作する。言語だけで速度を判断せず、モデル待ち時間と検索時間を測る。

Go案ではBedrockとS3 VectorsをAWS SDKで呼ぶ。Python案でもLangChainのAWS連携はAWS SDKを利用する。段階1で必要APIを呼べる依存パッケージの版を確認する。FastAPIを推す理由は文書処理とRAG評価をPythonにまとめられることであり、Bedrockの利用にPythonが必須という意味ではない。

## LangChain・LangGraph・LangSmithの採用判断

今回の推奨は「LangChainの一部コンポーネントをMVPで採用、LangGraphは拡張時、LangSmithは評価段階で任意採用」とする。LangChainの導入だけで検索品質が上がるとは扱わず、同じ評価セットで品質を確認する。

| 対象 | 役割と利点 | 今回の判断・負担 |
| --- | --- | --- |
| LangChain / langchain-aws | Bedrockモデルの呼び出し、メッセージ・出力の扱いを共通化する。構造化出力やモデル呼び出しのストリーミングを試しやすい | Bedrock接続と文書分割に限定して採用。依存パッケージの版、モデル固有の機能、例外・トークン情報の扱いを検証する |
| LangGraph | 分岐・反復・状態保存・人の確認を含む処理をグラフで管理できる | MVPでは見送る。固定の検索→回答には通常のusecaseで対応できる。将来、検索結果不足時の再検索や途中再開が必要なら導入する |
| LangSmith | モデル呼び出し等の追跡と評価結果を画面で比較できる | 段階4で自作資料を使って試す候補。外部サービスの契約・料金・送信データを確認する。利用しなくてもローカル評価とCloudWatchで運用できる |
| AWS SDKのみ | AWS APIのパラメータとレスポンスを直接制御でき、追加の抽象化を減らせる | S3 Vectors・S3・DynamoDB・SQSに採用。Bedrockも直接呼び出せるため、LangChainで必要機能が扱えなければ該当アダプターだけ切り替える |

### MVPで使うコンポーネント

1. `langchain-aws`の`ChatBedrockConverse`を回答生成に使う。選定モデルのConverse対応を確認し、トークン量・タイムアウト・ストリーミング・構造化出力の必要機能を検証する。
2. `langchain-aws`の`BedrockEmbeddings`を文書・質問のembeddingに使う。必要なモデル・次元数を指定できることを検証し、未対応の場合はembedding部分をAWS SDKで実装する。
3. `langchain-text-splitters`の`RecursiveCharacterTextSplitter`を分割の出発点にする。日本語の句点・改行等を考慮し、PDFはページ単位の抽出結果を分割して出典を維持する。重複幅・サイズは評価で調整する。
4. S3 Vectorsはboto3で保存・検索・削除する。LangChain側にも連携実装はあるが、今回はチャンク本文をS3に置く構成、権限フィルター、版管理、削除の制御を直接実装するためSDKを選ぶ。

LangChainの型は`infrastructure`内でアプリの型へ変換し、domain・usecase・HTTPレスポンスへ広げない。認可・フィルター・引用の検証・再試行・予算上限はアプリ側で実装する。依存は必要なパッケージだけを追加し、uv lockfileで固定する。

LangChainのモデル呼び出しがストリーミングできても、Lambda・API Gatewayを経由したSSEが成立するとは限らない。AWS上の経路は段階4で別に検証する。同期呼び出しがFastAPIのイベントループを塞がないよう、実行方法も確認する。

### 拡張時の導入条件

LangGraphは「検索→根拠不足の判定→質問の書き換え→再検索→回答」のような分岐・反復が要件になった場合に導入する。反復回数・合計トークン・制限時間を定め、通常RAGとの品質・費用の差を評価する。会話履歴を持つだけなら導入しない。途中再開が必要な場合は永続checkpointの保存先を設計し、Lambdaのメモリ内だけに置かない。文書取り込みのSQSとDLQは別の責務として維持する。

LangSmithを試す場合は、LangChainと独立した任意の追跡機能として扱う。自作資料と評価用の質問に限定し、入力・出力・取得文書の送信範囲を明示する。通常デプロイでは追跡を無効にし、API key未設定・サービス停止でも回答と評価スクリプトが動くようにする。AWS内で完結させたい場合は採用せず、CloudWatchとローカルの評価結果を使う。

段階1でAWS SDKによる小さな疎通検証を行い、LangChainのアダプターで必要な情報を保持できることを確認する。MVPでは1つの実装に絞り、両方のBedrockアダプターを継続保守しない。採用理由・依存の版・確認結果はADRに残す。

## MVPの範囲

1. Cognitoでログイン・ログアウトし、未認証のAPI利用を拒否できる。
2. アップロード権限を持つユーザーが画面からMarkdown・テキスト・テキスト抽出可能なPDFをアップロードし、進捗、取り込み状態、失敗理由を確認できる。初期の権限は管理者に限定する。
3. 利用者がチャットを新規作成し、複数ターンで文書に質問できる。回答と文書名・ページまたは見出し・引用箇所を確認し、保存した会話を再表示・継続できる。
4. 根拠が不足する質問には回答不能を返し、文書削除後は検索・原文表示の対象から外れる。
5. 文書一覧、カテゴリ絞り込み、原文表示ができる。管理者と利用者の権限を分け、評価データと実測結果をリポジトリに残す。

初期対象外：音声、OCR、Office文書、営業ロールプレイ、エージェント、複数テナント、複数embeddingモデル。ストリーミングは通常の回答が動いてから追加する。

### 必須機能の実装内容

| 機能 | 実装内容 | 完了条件 |
| --- | --- | --- |
| Cognito認証 | User Pool、managed login、Authorization Code + PKCE。ブラウザ用app clientはsecretを持たない。APIにはaccess tokenを渡す | ログイン・ログアウト、セッション更新、期限切れ時の再ログインが動く。未認証・不正なtoken・権限不足を拒否する |
| ファイルアップロード | ファイル選択、署名付きPOSTで隔離用S3へ送信、進捗表示、完了APIによるversion固定、非同期の検証・取り込み、失敗時の再試行と削除 | 対応ファイルを登録すると検索可能になる。上限超過・形式偽装・不正な所有者を拒否し、完了後の差し替えを取り込まない |
| チャット | 新規会話、メッセージ送信、202でジョブ受付、結果のポーリング、回答と引用表示、履歴一覧・再開・削除。生成中・結果不明・失敗の表示 | 30秒を超える生成と追加質問に対応し、再読み込み後もジョブと履歴を取得できる。他ユーザーの会話を閲覧・更新できない |

チャットは文書に基づくRAGチャットを必須とする。文書検索を使わない一般チャットは追加候補とする。会話ID・所有者・時刻と、メッセージの役割・本文・引用・生成状態を保存する。削除した文書への引用は閲覧不可として表示する。

生成時にはサーバー側で取得した直近の会話をトークン上限内で使う。会話を踏まえた検索用質問の作り方は評価対象にし、検索クエリ作成でモデルを呼ぶ場合は費用も記録する。会話全体を無制限にモデルへ渡さない。送信にはidempotency keyを付け、再送時の重複保存・同時生成を制御する。外部モデル呼び出しの結果が不明な障害では二重課金を完全に防げるとは約束せず、自動再生成せずに状態を表示する。

API契約には文書のアップロード開始・完了・状態取得・削除と、会話の作成・一覧・取得・削除・メッセージ送信を含める。所有者IDはCognitoの`sub`からサーバー側で決める。

### ロールと操作権限

| 操作 | 管理者（admin） | 通常ユーザー（user） |
| --- | --- | --- |
| RAGチャット、引用・登録文書の閲覧 | 可 | 可 |
| 自分の会話の一覧・再開・削除 | 可 | 可 |
| 他ユーザーの会話の閲覧・変更 | 不可 | 不可 |
| 文書のアップロード・カテゴリ設定・取り込み再試行・削除 | 可 | 不可 |
| 管理画面・取り込み失敗の詳細確認 | 可 | 不可 |

MVPは1つの共有ナレッジを両ロールが参照する。管理者ロールだけを理由に他ユーザーの会話へアクセスさせない。文書単位の個別共有やユーザー管理画面は追加候補とする。

Cognito User Poolのgroupを`admin`・`user`として定義し、初期ユーザーの割り当ては運用手順で行う。MVPでは各ユーザーをどちらか一方に所属させ、所属なし・未知のロールはアプリの利用を拒否する。通常ユーザーが画面やAPIから自分を管理者へ変更できないようにする。管理者の初期登録・ロール変更は運用者が行い、変更後のtoken更新と権限反映も確認する。

APIは検証済みaccess tokenの`cognito:groups`とDynamoDBの現在のユーザー状態・ロールを照合し、リクエスト本文のロール指定を信用しない。ロール変更は先にアプリ側で利用を停止してからCognitoへ反映する。Nuxtの管理画面へのアクセス制御に加え、アップロードURLの発行・取り込み依頼・再試行・文書削除の各APIでも管理者権限を検証する。

## モノレポ

```text
rag-portfolio/
├── frontend/                 Nuxt 4 + Tailwind CSS 4
│   └── app/                  pages、components、composables
├── backend/
│   ├── src/
│   │   ├── api/              HTTP、認証、入力・出力
│   │   ├── usecase/          登録・検索・回答の処理
│   │   ├── domain/           文書・引用・権限、外部接続の契約
│   │   ├── infrastructure/   Bedrock、S3、S3 Vectors、DynamoDB
│   │   └── workers/          取り込み・削除・チャット生成・配送・回復処理
│   └── tests/
├── infra/                    AWS CDK v2 / TypeScript
├── packages/api-client/      OpenAPIから生成するTypeScript型・クライアント
├── evals/                    質問・正解根拠・評価スクリプト・結果
├── fixtures/                 公開可能な自作サンプル文書
├── docs/                     構成図、ADR、運用手順、評価の説明
└── .github/workflows/        CI、AWSへのデプロイ
```

依存は `api → usecase → domain`。外部接続はdomainの契約を実装し、起動時に注入する。HTTPスキーマはPydantic、業務の型は必要に応じて分ける。ルートのpnpm workspaceはfrontend・api-client・infraを管理し、Pythonはuvと専用lockfileを使う。

## AWS構成案

```text
ブラウザ
  ├─ CloudFront → 非公開S3：Nuxtの静的生成物
  ├─ Cognito：ログイン
  └─ API Gateway HTTP API → Lambda：FastAPI
        ├─ DynamoDB：ユーザー状態・文書状態・チャット履歴・ジョブ・outbox
        ├─ S3：原文・抽出テキスト
        ├─ S3 Vectors：検索用ベクトル
        ├─ Bedrock：embedding・回答生成
        └─ DynamoDB Streams → dispatcher → SQS
              ├─ document worker：取り込み・削除 → DLQ
              └─ chat worker：検索・回答生成 → DLQ
```

Nuxtは紹介ページを静的生成し、ログイン後の画面はブラウザからAPIを呼ぶ。サーバー側Nuxt機能が必要になったらホスティングを再検討する。Tailwind CSSは公式のNuxt向けViteプラグイン構成を使う。

APIはジョブ受付と結果取得を通常のJSONレスポンスで返し、FastAPIのLambda実行にはASGIアダプターを使う。HTTP APIの最大integration timeoutは30秒なので、回答生成を同期API内で待たない。メッセージ送信は202とジョブIDを返し、ブラウザが結果をポーリングする。S3アップロードは署名付きPOSTでサイズ上限・保存先を制約し、完了APIが所有者・実データ・S3 version IDを確認する。状態変更とoutboxを同じDynamoDBトランザクションで保存し、dispatcherがSQSへ配送する。

CognitoはCDKでUser Pool・app client・ログイン用ドメイン・`admin`と`user`のgroupを定義する。APIではaccess tokenの署名・発行元・期限・`token_use`・許可したclient・必要scopeを検証する。現在のユーザー状態とセッション失効もAPIで確認する。ログアウトはアプリ側のセッション失効を記録し、Cognitoのtokenとログインセッションを処理する。JWTの署名と期限の検証だけでは、Cognitoで失効したtokenを拒否できない。

CDKはStorage・Auth・Compute・Frontendに責務を分ける。IAMはAPI・dispatcher・document worker・chat workerで分離する。S3は非公開、静的サイトのS3だけをCloudFrontからOACで参照する。原文のダウンロードは認可後に有効期限2分の署名付きURLを発行し、アプリの配信元とは別のS3 originからattachmentとして提供する。発行済みURLは即時失効するとは扱わない。

初期はdevの1環境。公開用環境を追加する際は設定・データ・リソースを分ける。環境ごとの長期ブランチは作らず、mainからGitHub ActionsのEnvironmentを指定して反映する。AWS認証はOIDCを使い、長期アクセスキーを保存しない。

## RAGの実装

取り込み・検索・回答の流れはアプリケーション側で実装し、Bedrock接続と分割にLangChainのコンポーネントを使う。S3 VectorsはAWS SDKで直接操作する。Bedrock Knowledge Basesの採用は必須条件に含めない。

1. 原文からテキストを抽出し、文書ID・版・ページまたは見出しを維持して分割する。Bedrockのembeddingモデルを1つ選び、質問にも同じモデル・次元数を使う。
2. チャンク本文をS3、ベクトルと検索用メタデータをS3 Vectorsへ保存する。チャンクIDは再実行で重複しないよう決める。
3. 質問をベクトル化し、権限・カテゴリで絞って上位候補を検索する。DynamoDBの状態も確認し、削除済み・旧版・処理中の文書を回答に混ぜない。
4. 取得した根拠と質問をBedrockへ渡す。文書内の命令は実行対象にせず、根拠に含まれる情報だけを使うよう指示する。引用IDはAPI側で取得候補に存在するか検証する。
5. 評価結果を見て、チャンクサイズ・件数・rerank・親子チャンクを比較する。変更前後で同じ評価セットを使う。

処理状態は `uploading → queued → validating → processing → ready / failed` とし、削除は `deleting → deleted` を持つ。重複配信、途中失敗、再試行を考慮する。削除開始時に検索対象から外し、workerが状態・処理世代を確認して削除済み文書を復活させない。MVPでは既存文書の上書き更新は提供せず、新規登録と削除に絞る。

MVPではファイル上限を仮に10MiB・100ページ・抽出20万文字・500チャンクとする。タイムアウトに収まらない資料は失敗理由を表示し、長時間処理の需要が確認できたらECSタスク等へ移す。Lambdaは最大15分なので、大きな文書の取り込みを無制限に任せない。

## 実行順序と完了条件

| 段階 | 作業・成果物 | 完了条件 |
| --- | --- | --- |
| 1. 選定と構成の成立確認 | 技術・公開方式・利用枠のADR、API契約、データモデル、状態遷移。小さな検証でBedrock/S3 Vectors、LangChain、Cognito、S3 POST/version固定、非同期job/outboxを確認する | 必須サービスを利用でき、1文書のRAGと小さな非同期jobが通る。token/group・version固定・配送失敗からの回復を確認し、依存の版と概算費用を記録する |
| 2. ローカルMVPと業務ルール | モノレポ、Nuxt画面、FastAPI、LangChainアダプター、非同期jobのfake、サンプル資料。認可・idempotency・状態遷移・引用・入力上限を実装する | アップロード→取り込み→チャット→履歴再開が通る。ロール・所有者・重複送信・削除競合のテストが通り、AWSを使う検証とfakeの検証を区別できる |
| 3. AWSへ接続 | CDK、Cognitoログイン、S3署名付きPOST、outboxとdispatcher、document/chat worker、DynamoDB、ジョブ取得と会話履歴、CI/CD | ログイン→アップロード→取り込み→チャット→履歴再開→削除がAWS上で通る。30秒を超える生成、失効・権限の拒否、取り込みと削除の競合、重複配信と配送失敗を確認できる |
| 4. 評価・セキュリティ・運用検証 | 固定評価セット、検索調整、XSS・悪意ある文書・形式偽装の検証、IAM/CORS/CSP、利用枠、監視、停止・復旧。LangSmithとSSEは必要な場合だけ検証する | RAGの改善と残る失敗を説明でき、設計書の公開前検証に結果が揃う。上限到達時の停止と復旧、外部追跡なしの評価が動く |
| 5. ポートフォリオ仕上げ | README、構成図、ADR、デモ動画、評価結果、運用・停止手順、公開前のセキュリティ検証 | 初見の人が起動し、設計判断・実測結果・制約を確認できる。設計書の公開前チェックが通り、利用上限・停止・復旧を確認できる |

各段階は完了条件を満たしてから次へ進む。セキュリティは段階4で初めて追加するのではなく、段階1の契約と段階2の業務ルールから実装する。段階4で実AWSを含む検証結果を揃え、段階5ではその結果と公開設定を確認する。成功済み検証は変更・新しい懸念がある場合だけ再実行する。

### 最初に作るIssueの単位

1. **選定ADRと検証条件**：repo名、バックエンド・基盤・DB、リージョン・モデル、公開方式、予算を整理する。
2. **1文書のRAG**：ページを保持して分割し、embedding→S3 Vectors検索→引用付き回答を通す。
3. **認証とロール**：Cognitoのログイン、access token、現在のrole、ログアウト・権限解除の拒否を通す。
4. **安全なアップロード**：署名付きPOST、サイズ制限、version固定、実内容の検証、取り込み状態を通す。
5. **非同期ジョブの成立**：202→outbox→queue→worker→結果取得を通し、重複・配送失敗・結果不明・削除競合を確認する。

これらは着手後に作るIssueの内容案であり、GitHubへの作成・投稿はまだ行っていない。

## セキュリティの実装と公開条件

| 対象 | 必須対策 | 組み込む段階 |
| --- | --- | --- |
| 認証・認可 | access token検証、現在のrole/利用停止/セッション失効、owner確認、管理APIの拒否 | 段階1で契約・疎通、段階2で実装、段階3で実AWS検証 |
| ファイル | 非公開の隔離領域、署名付きPOST、version固定、形式・容量・抽出上限、完了後差し替えの防止 | 段階1で成立確認、段階2〜3で実装、段階4で異常入力検証 |
| チャット・RAG | idempotencyと利用枠、取得候補内の引用検証、モデルへ権限を委譲しない、Markdown sanitizeと危険URL・画像の制限 | 段階2で実装、段階3〜4で競合・攻撃入力検証 |
| AWS・CI・運用 | IAM分離、S3非公開、CORS/CSP/no-store、OIDC限定、secret・依存検査、本文/tokenをログに出さない、停止・復旧 | 段階3で構築、段階4で検証、段階5で公開設定を確認 |

公開前に [設計書の公開前検証](rag-portfolio-design.md#11-公開前の検証) を通し、結果・ログ・未解決事項を記録する。既知の認可違反・XSS・削除後の復活・無制限な生成や取り込みが残る場合は公開を進めず、対応して再検証する。

文書削除は新規検索・URL発行の停止と非同期の物理削除を含む。発行済み原文URLには最大2分の有効期間があり、過去のチャット本文・監査・バックアップからの即時消去は含まない。ログアウトはアプリ側の失効確認を含む。これらの範囲を画面とREADMEにも記載する。

初期デモは運用者が用意した自作資料に限定する。第三者からの任意ファイルを受け入れる場合は、マルウェア検査と隔離・検査失敗時の拒否を導入する。予算・MFA・保持期間の初期案は公開前に確定する。

## 検証と運用

評価セットはまず30問程度を自作し、回答可能・回答不能・言い換え・文書間矛盾・文書内の悪意ある命令を含める。調整用と固定の確認用を分け、確認用を見ながら調整した場合は結果を独立した評価として扱わない。検索は正解チャンクのRecall@k、回答は引用の整合性・根拠への忠実性・回答不能の正しさを測る。モデル・プロンプト・データ版を結果に記録する。

目標は暫定でRecall@5が80%以上、引用リンクの機械的整合性100%、実施した権限検証で違反0件とする。Recallの母数は根拠が存在する質問だけとし、回答不能の質問は別に集計する。初回測定後に見直し、30問の結果を一般的な性能として扱わない。応答時間は待ち行列・検索・生成・取得を分け、初回と通常時を区別してp50/p95と測定件数を報告する。入力・出力トークン等から1質問あたりの費用を見積もる。

CIではfrontendの型チェック・ビルド、backendのlint・型チェック・業務テスト、OpenAPI生成差分、CDK synthを行う。E2Eはログインからファイルアップロード・引用表示・追加質問・履歴再開までと権限拒否を中心にする。管理者の文書管理、通常ユーザーのチャット、通常ユーザーによる管理API呼び出しの拒否、両ロールによる他ユーザー会話へのアクセス拒否を検証する。実AWSを使う評価は明示実行とし、通常CIで毎回課金を発生させない。

CloudWatchにrequest ID・処理時間・エラー・トークン量を残し、質問本文や原文を常時ログに出さない。失敗率、DLQ、利用量を監視する。公開デモは自作資料を使い、一般利用者にはアップロード権限を与えない。

公開前に月額予算を決め、実際の構成をAWS Pricing Calculatorで確認する。DynamoDBの条件付き更新等でユーザー別・全体の日次利用枠を予約し、入力長・出力トークン・同時実行数にも上限を設定する。AWS Budgetsの通知は支出の強制停止ではないため、API側の受付停止も実装する。不要なログ・データの保持期限と削除方針を決める。

## 構成を変える条件

| 条件 | 変更 |
| --- | --- |
| Goの採用実績を示すことが最優先 | 段階1でGoを選び、OpenAPIと文書処理の実装方法を決める |
| ECS・SQL・マイグレーションの実績が主目的 | ECS Fargate・RDS PostgreSQL・Alembicへ変更し、ALB・VPC・接続・固定費を見積もる |
| 取り込みがLambdaの制限に収まらない | workerをECSタスク等へ移す。APIと検索契約は維持する |
| SSEが必要 | Lambda Web Adapterと対応経路を小さく検証する。初期HTTP APIとASGIアダプターで逐次表示できるとは仮定しない |
| 検索品質が目標を満たさない | 評価の失敗を分類し、rerank・親子チャンク等を個別に比較する |
| 再検索の分岐・反復や途中再開が要件になる | LangGraphを導入し、反復上限・永続checkpoint・評価を追加する |
| 追跡画面と評価実験の比較が必要になる | 段階4でLangSmithを検討し、費用と送信データを確認する |

## 公式資料

- Nuxtは静的生成・Nodeサーバー等の配置方法を提供する：[Nuxt deployment](https://github.com/nuxt/nuxt/blob/main/docs/1.getting-started/16.deployment.md)。
- Nuxt向けTailwind導入はViteプラグイン構成を確認する：[Tailwind CSS with Nuxt](https://tailwindcss.com/docs/installation/framework-guides/nuxt)。
- FastAPIはOpenAPIとクライアント生成に対応する：[FastAPI features](https://fastapi.tiangolo.com/features/)。
- S3 Vectorsの検索・メタデータ仕様：[Querying vectors](https://docs.aws.amazon.com/AmazonS3/latest/userguide/s3-vectors-query.html)、[Metadata filtering](https://docs.aws.amazon.com/AmazonS3/latest/userguide/s3-vectors-metadata-filtering.html)。
- CDKにはS3 Vectors indexのL1 constructがある：[CfnIndex](https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.aws_s3vectors.CfnIndex.html)。実装時にvector bucketを含め必要リソースとSDKの版を固定する。
- 配置前にリージョン対応を確認する：[S3 Vectors regions and quotas](https://docs.aws.amazon.com/AmazonS3/latest/userguide/s3-vectors-regions-quotas.html)。モデルの利用可否も実際のAWSアカウントで確認する。
- Lambdaの実行時間制限：[Lambda timeout](https://docs.aws.amazon.com/lambda/latest/dg/configuration-timeout.html)。
- FastAPIのLambdaストリーミング例：[AWS Lambda Web Adapter example](https://github.com/aws/aws-lambda-web-adapter/blob/main/examples/fastapi-response-streaming-zip/README.md)。認証・公開経路はこの例とは別に設計する。
- LangChainのBedrock接続：[ChatBedrock integration](https://docs.langchain.com/oss/python/integrations/chat/bedrock)。Converse・構造化出力・ストリーミング等の対応は選定モデルでも確認する。
- embeddingとS3 Vectorsの連携実装：[BedrockEmbeddings](https://reference.langchain.com/python/langchain-aws/embeddings/bedrock/BedrockEmbeddings)、[S3 Vectors integration reference](https://reference.langchain.com/python/langchain-aws/vectorstores/s3_vectors/base)。採用版のAPIは段階1で検証する。
- 分割コンポーネント：[Recursive text splitter](https://docs.langchain.com/oss/python/integrations/splitters/recursive_text_splitter)。
- LangGraphの役割・永続化：[LangGraph overview](https://docs.langchain.com/oss/python/langgraph/overview)。
- LangSmithの追跡導入と料金：[Tracing quickstart](https://docs.langchain.com/langsmith/observability-quickstart)、[Plans and pricing](https://www.langchain.com/pricing)。
- Cognitoの認証フローとaccess token：[Authorization endpoint / PKCE](https://docs.aws.amazon.com/cognito/latest/developerguide/authorization-endpoint.html)、[Understanding the access token](https://docs.aws.amazon.com/cognito/latest/developerguide/amazon-cognito-user-pools-using-the-access-token.html)。
- HTTP APIの30秒制限：[HTTP API quotas](https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-quotas.html)。
- JWTの失効検証の注意点：[Cognito token revocation](https://docs.aws.amazon.com/cognito/latest/developerguide/token-revocation.html)。
- データ保存と配送の不整合対策：[Transactional outbox](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html)。
