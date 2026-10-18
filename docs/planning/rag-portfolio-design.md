# RAGポートフォリオ設計書

作成日：2026-10-12。対象はリポジトリ作成前の設計。コード・AWS環境による動作検証は未実施。

## 1. 要件と採用方針

必須条件は、Nuxt 4・Tailwind CSS系のフロントエンド、モノレポ、CDKによるAWS構築、Bedrock、S3 Vectors、ファイルアップロード、複数ターンのチャット、Cognito認証、管理者と通常ユーザーの2ロール。

推奨案はFastAPI、LangChainのBedrock・分割コンポーネント、Lambda、DynamoDB。バックエンド言語・実行基盤・DBはユーザーの最終選定前の推奨として扱う。LangGraph・LangSmith・SSE・一般チャット・文書上書き更新はMVPの必須にしない。

初期の公開方式は招待したユーザーだけがログインするデモとする。セルフサインアップは無効。登録文書は公開可能な自作資料に限定し、全ユーザーで共有する。公開管理者アカウントは配布しない。文書を個別共有する場合は、この共有モデルと検索フィルターを改めて設計する。

## 2. 処理構成と信頼境界

```text
Browser ─ CloudFront/OAC ─ Static-site S3
   ├──── Cognito managed login / PKCE
   ├──── Upload S3：署名付きPOST、API発行の保存先のみ
   └──── HTTP API ─ FastAPI Lambda ─ DynamoDB
                                      ├─ メタデータ・会話・ジョブ・利用枠
                                      └─ outbox / Streams ─ Dispatcher ─ SQS
                                           ├─ Document worker / DLQ
                                           │    └─ S3 / Bedrock embedding / S3 Vectors
                                           └─ Chat worker / DLQ
                                                └─ S3 / S3 Vectors / Bedrock generation
```

ブラウザのユーザーID・ロール・S3 key・引用URL・履歴本文を権限判断の根拠にしない。SQSには原文・質問・tokenではなくジョブIDと処理世代を送る。workerはDynamoDBから所有者・状態・権限を取り直す。アップロード文書とモデル出力は、管理者が登録したものでも信頼しない。

APIは受付・一覧・状態取得を短時間で返す。モデル生成は非同期workerで実行し、メッセージ送信は202とjob IDを返す。画面は2秒から最大10秒へ間隔を伸ばしてポーリングし、非表示時は停止する。再読み込み時には既存jobを取得する。回答生成が30秒を超えてもAPI接続を保持しない。[HTTP APIの制限](https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-quotas.html)

## 3. 認証・ロール・失効

Cognito User Poolとsecretなしのpublic app clientを使い、Authorization Code + PKCE（S256）でログインする。OIDC対応ライブラリを使ってstate・nonce・callbackを検証する。callbackとlogout URLは環境ごとに固定する。API認証にはaccess tokenを使い、ID tokenを受け付けない。

API GatewayのJWT authorizerとAPI内の共通認証処理で署名・issuer・期限・client・`token_use`・scopeを検証する。JWKSは固定のCognito issuerから取得し、任意のURLやJWT指定のアルゴリズムを受け付けない。内部用途でもtokenをログに出さない。

CDKでCognito resource serverと`rag-api/use` scopeを定義し、OAuthの取得scopeとAPIの要求scopeを一致させる。ブラウザへAWSアクセスキーを渡さず、S3操作はAPIが発行したPOST条件と短期URLだけを使う。Cognito Identity PoolはMVPでは不要とする。

| 操作 | admin | user |
| --- | --- | --- |
| 登録文書の閲覧、RAGチャット、自分の履歴管理 | 可 | 可 |
| 文書登録、カテゴリ設定、再試行、削除 | 可 | 不可 |
| 他ユーザーの会話、ジョブ、メッセージの閲覧・変更 | 不可 | 不可 |
| ロール変更・ユーザーの利用停止 | 運用者がAWS権限を使う。MVPのアプリ画面には提供しない | 不可 |

`cognito:groups`は`admin`・`user`のいずれか1つとする。所属なし・両方所属・未知のgroupは拒否する。APIはUsersの現在のrole・enabledを強整合読み取りし、tokenのroleと照合する。Usersの正規レコードを読めない場合は拒否し、GSIや古いキャッシュで許可しない。

ロール変更はUsersを一旦disabledにする→Cognito group変更→Cognitoのセッション失効→Usersのroleを反映してenabledにする、という運用処理にする。途中失敗はdisabledのまま残して修復する。古いadmin tokenだけで文書管理を続けられないことを検証する。

ログアウトAPIはaccess tokenの`origin_jti`をセッション失効レコードへ保存する。APIは各リクエストで失効状態を確認する。失効記録の保存後にrefresh tokenの失効とCognitoログインセッションの終了、ブラウザのtoken破棄を行う。access tokenは暫定10分、refresh tokenは暫定1日とし、失効記録は当該refresh tokenからtokenを発行できる期間より長く保持する。TTLの削除時刻は権限判断に使わない。

このアプリのログアウトは当該セッション、運用者の利用停止は全セッションを対象とする。Cognitoで失効してもJWTの署名・期限だけを検証するライブラリはtokenを許可し得るため、アプリ側の確認が必要。[Cognito token revocation](https://docs.aws.amazon.com/cognito/latest/developerguide/token-revocation.html)

ブラウザのtokenはメモリに保持し、再読み込み時にはCognitoへ再認証する。PKCE verifier等の短期情報だけをsessionStorageへ置き、callback処理後に削除する。refresh tokenをlocalStorageへ永続保存しない。MFAは公開前に有効化し、初期案は招待ユーザー全員にTOTPを必須にする。管理者だけに限定する案を選ぶ場合は、管理者のMFAを強制する方法を別途検証する。

## 4. ファイルアップロード

1. adminがアップロード開始APIを呼ぶ。APIは現在の権限、利用枠、宣言した形式・サイズを検証し、サーバー生成document IDとランダムなS3 keyを保存する。
2. 期限5分の署名付きPOSTを返す。policyでkeyと`content-length-range`を固定する。ファイル本体をAPI Gatewayに通さず、quarantine用の非公開S3へ送る。
3. 完了APIはサーバー側のkeyと実オブジェクトのサイズ・version IDを確認し、versionを固定する。再度完了を呼んでも同一結果を返す。clientのContent-Typeは検証の代わりにしない。
4. workerが固定versionの内容を検証・抽出する。成功した原文を公開用文書領域にコピーし、抽出本文・チャンクmanifest・ベクトルを作る。quarantineのkeyを原文配信に使わない。
5. 検証失敗は公開・検索せず、画面に安全なエラーコードを返す。未完了アップロードは期限後に回収し、S3旧versionもlifecycleで回収する。

署名付きURLは期限まで再利用でき、同じkeyへの書き込みで差し替えが起きる。version固定とquarantine分離で「確認した内容と取り込んだ内容が違う」状態を防ぐ。期限切れの前に完了したURLが自動で使用不能になるとは扱わない。[S3 presigned URL仕様](https://docs.aws.amazon.com/AmazonS3/latest/userguide/using-presigned-url.html)

初期限度は10MiB・100ページ・抽出20万文字・500チャンクまで。拡張子の許可リストと実データの検証を行い、暗号化PDF、破損PDF、HTML、アーカイブ、Office文書、実行ファイルを拒否する。テキストは文字コードとNUL等を検証する。PDF解析には時間・メモリ・出力量の上限を設け、埋め込みURLやスクリプトを実行しない。workerのAWS権限は必要な領域に限定する。

初期デモは運用者が用意した資料に限定する。第三者が持ち込む任意ファイルを受け付ける運用へ変更する前に、マルウェア検査・隔離と検出失敗時の拒否を追加する。検査サービスの採用と費用はその時点で決める。パーサーの制限だけでマルウェア検査を代替したとは扱わない。[OWASP File Upload](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html)

## 5. データモデルとAPI契約

初期は責務別のDynamoDBテーブルとし、アクセスパターンを明示する。文書一覧・会話一覧はcursorでページングする。全件Scanを主要なリクエスト処理に使わない。

cursorは対象API・owner・フィルターと結び付けて検証し、clientが任意のpartition keyを指定できないようにする。GSIで取得した一覧は正規レコードの現在の状態を再確認して返す。失効・削除の許可判断にGSIの古い値を使わない。

| テーブル | 主キー・用途 |
| --- | --- |
| Users | `sub`。現在のrole、enabled、監査時刻 |
| RevokedSessions | `sub + origin_jti`。失効セッションと保持期限 |
| Documents | document ID。状態、カテゴリ、所有者、S3 key/version、処理世代。共有ナレッジの作成時刻順GSI |
| Conversations | conversation ID。owner sub、状態、active job、最新メッセージ番号。ユーザー別更新時刻GSI |
| Messages | conversation ID + sequence。1メッセージ1item、role、本文、引用、状態 |
| Jobs | job ID。owner、対象ID、status、期限、lease、処理世代、結果・エラーコード。期限別の回復対象GSI |
| Outbox | event ID。job ID、配送状態、期限。未配送の回復対象GSI |
| Usage | 日付 + global/user/document等の枠。予約済みトークン相当量と実績 |

会話全文や原文を1itemへ蓄積しない。引用にはdocument ID・固定版・page/heading・chunk IDを保存し、署名付きURLを保存しない。原文・チャンク・ベクトルID manifestはS3へ置く。1メッセージのUTF-8本文は64KiB以下とし、属性・引用を含むitemサイズも検証する。[DynamoDBの400KB制限](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Constraints.html)

| API | 応答・主要な検証 |
| --- | --- |
| `POST /documents/uploads` | adminのみ。document ID、POST条件、期限を返す |
| `POST /documents/{id}/complete` | adminのみ。固定key/versionを確認し、202でjobを返す |
| `GET /documents`、`GET /documents/{id}` | 利用可能な共有文書と状態。詳細エラーはadminのみ |
| `GET /documents/{id}/download` | 状態・引用の固定版・権限を確認して短期URLを返す |
| `POST /documents/{id}/retry`、`DELETE /documents/{id}` | adminのみ。状態遷移を条件付き更新し、202を返す |
| `POST /conversations`、`GET /conversations` | 認証subで会話作成・自分の会話一覧 |
| `GET /conversations/{id}`、`GET /conversations/{id}/messages` | owner確認、cursorによる取得 |
| `POST /conversations/{id}/messages` | owner確認。idempotency key必須、202とjob IDを返す |
| `DELETE /conversations/{id}` | owner確認。即時に利用不可へ変更し、非同期にデータ削除 |
| `GET /jobs/{id}` | ownerまたは文書管理adminを確認。状態・結果・安全なエラーを返す |
| `POST /auth/logout` | 当該セッションの失効を記録する |

idempotency keyはownerと操作の範囲で一意にし、入力hashも保存する。同一key・同一入力は既存結果、同一key・別入力は409。保持期間は24時間を初期値とする。保護対象の不正IDは404、ロール不足は403、入力不正は422、上限超過は429、依存障害は503とし、存在確認による情報漏れを避ける。

同じ操作のjob IDはowner・操作・idempotency keyから決定し、Jobsの条件付き作成で重複を拒否する。uploadの完了・再試行・削除にもこの規則を適用する。削除済みのjobをTTLで消す場合も、約束した24時間の重複防止情報は別のJobs itemとして維持する。

## 6. 配送・再試行・同時処理

APIはジョブ・必要な状態変更・利用枠の予約・outboxをDynamoDBの同じtransactionで保存する。DB保存とSQS送信を独立した成功条件にしない。Streamsはoutbox作成だけをdispatcherへ通知し、dispatcherはSQSへ送ってから配送済みへ変更する。配送の重複は許容し、worker側で吸収する。[Transactional outbox](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html)

document/chatのqueueとDLQは分ける。初期batch sizeは1。workerは条件付き更新でleaseを取得し、期限と処理世代を確認する。完了済み・削除中・旧世代のjobは再実行しない。取り込みはチャンク処理のcheckpointを保存し、同一chunk IDへの保存で再試行可能にする。上限に収まらない文書は明確にfailedへ移す。

文書状態は`uploading → queued → validating → processing → ready`、失敗は`failed`、削除は`deleting → deleted`とする。chat jobは`queued → retrieving → invoking → completed`とし、`failed / outcome_unknown / cancelled / expired`を終端状態に持つ。画面が待ち続けないよう、queuedの期限は暫定5分、開始後の生成期限はworker timeoutで管理する。

chatは1会話につき同時に1jobとする。Messagesの連番・active jobの取得・利用枠の予約をtransactionに含める。workerは現在のユーザー・会話・文書状態を確認してから検索・生成する。モデル呼び出し直前に`invoking`を保存し、結果保存時にもlease・会話状態・参照文書の処理世代をtransactionで確認する。

モデル呼び出し前の一時障害は有限回の再試行を許可する。呼び出し開始後に結果が分からなくなった場合は`outcome_unknown`とし、自動で同じ生成を再実行しない。ユーザーが新しいkeyで再試行した場合は追加課金の可能性を画面で知らせる。副作用を伴う外部APIにexactly-onceを保証しない。

Lambda timeoutはAPI 15秒、chat worker 120秒、document worker 300秒を初期値として実測で調整する。SQS visibility timeoutはworker timeoutの6倍以上とbatch windowを考慮する。queueの最大同時実行数・Lambda reserved concurrencyを整合させる。[AWSのSQS設定指針](https://docs.aws.amazon.com/lambda/latest/dg/services-sqs-configure.html)

5分ごとのmaintenance処理で未配送outbox、期限切れlease、未完了upload、削除jobの停滞を確認する。pendingの復旧は必ず同一job ID・世代で行う。Streamsの再試行失敗、dispatcherの失敗、SQS DLQを監視し、失敗イベントの保存と再配送手順を用意する。通知だけで止まらず、回復処理の失敗も記録する。

jobの終了・失敗・期限切れでは同じjob IDに限って会話のactive jobを解除する。古いworkerが新しいjobのlockを解除しないよう条件付き更新する。結果不明の利用枠は保持し、確認できる失敗だけを安全に精算する。

## 7. RAGと引用

MVPは1embeddingモデル・1次元数・1distance metricを固定する。分割はページまたは見出しの境界を保ち、初期600文字・重複80文字を比較開始点とする。モデルのtoken制限は文字数だけでは保証できないため、実入力の上限も確認する。

S3 Vectorsのmetadataにはdocument ID・version・カテゴリ・chunk IDを置く。本文はS3のチャンクから読む。検索で上位20候補を取得し、現在のDocuments状態と世代を確認して最大5件を生成へ渡す。削除済み・未公開・旧世代はモデルへ送る前に除外する。カテゴリ以外に個別共有を導入する場合は、検索段階のアクセス制約も追加する。

初期は直近3ターンと現在の質問を上限内で扱う。質問は最大4,000文字かつUTF-8で16KiB以下、生成は最大2,048 output tokensを初期値とする。履歴と根拠を含む入力tokenの上限は選定モデルと費用見積もりで決め、履歴から削る順序を固定する。モデル・プロンプト・分割設定・検索設定の版を結果に残す。

過去のassistantメッセージは根拠として扱わず、引用文書が削除済みの回答は次の生成contextから除外する。追加質問の話題は利用者の過去の質問から引き継ぎ、今回取得した公開可能な文書を回答の根拠にする。検索結果が足りない場合に古い履歴だけから事実を補わない。

引用はモデルから候補内のcitation IDとして受け取り、APIで文書・ページ・chunkへ解決する。未知のID、任意URL、存在しないページは除外または生成失敗として扱う。引用IDの整合性と、本文が根拠を支持しているかは別の評価項目とする。検索候補がない場合はモデルを呼ばず、根拠不足を返す。

原文内の命令とsystem指示を分離するが、プロンプトだけで攻撃を完全に防げるとは扱わない。モデルにAWS認証情報・非公開の他ユーザー履歴・管理ツールを渡さない。モデル出力で権限を変更したり外部URLへアクセスしたりしない。[OWASP Prompt Injection](https://genai.owasp.org/llmrisk/llm01-prompt-injection/)

## 8. 削除・競合・保持

文書削除は最初にDocumentsを`deleting`へ変更し、世代を進めて取り込みの公開処理を無効化する。新規検索・ダウンロードURL発行を直ちに拒否する。生成完了のtransactionも参照した状態・世代が変わっていれば回答を公開しない。取り込みworkerは削除と競合してreadyへ戻せない。

削除workerはmanifestからベクトルを削除し、S3の公開版・抽出本文・quarantineの全versionを回収する。manifestはベクトル書き込みより先に永続化する。外部ストレージへの書き込みとDynamoDBの世代確認は原子的ではないため、削除の確定処理は古いworkerの最大実行時間とSDKの待ち時間を考慮して待ち、旧世代の書き込みが終わった後に再掃除する。S3 Vectorsからの削除が遅れても、Documentsの正規状態で候補を除外する。削除完了は各保存先の確認後に記録し、途中失敗は再試行する。

発行済みダウンロードURLは最大2分の有効期間があり、開始済みダウンロードや利用者が保存したコピーは回収できない。即時失効が必要になったら認可付き配信経路へ変更する。文書削除は既に保存したチャット本文からの引用文の除去を含まない。履歴には「参照文書削除済み」と表示する。このデータ削除範囲はREADMEと管理画面でも明示する。

会話削除は最初に会話を利用不可へ変更し、生成結果の保存を拒否する。Messages・Jobsは非同期に削除する。ログ・監査・バックアップに残る期間は別に定義し、全保存先からの即時消去と表現しない。

初期保持案は、履歴30日、処理ログ14日、監査記録90日、未完了upload 1日。ユーザー・セッション失効記録とidempotency情報は安全な期限まで保持する。公開用DynamoDBにPITRを設定し、S3のversioningと復旧手順を確認する。復元時には削除済みデータ・失効情報が古くなるため、復元環境を閉じたまま再適用してから公開する。

## 9. 画面・配信のセキュリティ

チャット・文書タイトル・引用を未検証HTMLとして描画しない。Markdownはraw HTMLを無効にし、出力をsanitizeする。`javascript:`・`data:`のリンク、リモート画像、自動URL fetchを許可しない。外部リンクには適切なrelを付け、原文は別originでattachmentとして配信する。[OWASP Improper Output Handling](https://genai.owasp.org/llmrisk/llm052025-improper-output-handling/)

CloudFrontにCSP・HSTS・X-Content-Type-Options・Referrer-Policy・frame制約を設定する。CSPはNuxtの静的生成物とCognitoリダイレクトで実際に検証し、必要なinline scriptはbuild時のhash等で許可する。広い`unsafe-inline`・`unsafe-eval`を無条件で追加しない。

APIとS3のCORSは環境ごとの正確なfrontend origin・必要method/headerだけを許可する。CORSを認証・認可の代わりにしない。保護APIはBearer tokenを使用し、認証cookieへ変更する場合はCSRF対策を追加する。個人別レスポンスは`Cache-Control: no-store`とし、共有CDNキャッシュに保存しない。

## 10. AWS権限・費用・監査

APIはモデル生成・ベクトルの書き換え権限を持たず、workerはCognito group変更権限を持たない。IAMはmodel/index/table/bucket prefixを限定する。S3・S3 Vectorsは公開許可を設定せず、保存時暗号化とTLSを使用する。初期LambdaはVPC外に配置し、NAT Gatewayを前提にしない。KMSのcustomer managed keyが必要なら用途・費用・権限を別途決める。

受付時にglobal/userの利用枠と同時job上限をtransactionで予約し、workerでも全体停止フラグを確認する。生成・embedding・再試行の費用を含めた予約と実績を分け、結果不明時は安易に予約を払い戻さない。Bedrockへの呼び出しごとにtimeout・有限のretry・token上限を設定する。

日次枠はUTCの日付で区切り、画面には更新時刻をJSTで表示する。API受付だけでなく各Bedrock呼び出し前にも残り予約を確認する。選定モデルの最大入力・出力と課金単位に基づき予約し、直接取得できないembedding token量は保守的な上限で管理する。無制限のSDK retryを既定値として残さない。

API Gatewayのthrottleに加え、アプリ側のユーザー別制限、polling制限、登録ファイル数・総容量・取り込み量の制限を設ける。予算超過時は新規生成・取り込みを停止し、既存履歴と削除は利用可能にする。AWS Budgets通知は補助とし、支出をゼロ超過にできる保証とは扱わない。

WAFはMVPで必須にしない。必要になったらCloudFront等の対応する配置先を選ぶ。HTTP APIへ直接配置できる前提で設計せず、直接API endpointへの迂回でもJWT・利用枠の制御が機能するようにする。[AWS WAFの対応リソース](https://docs.aws.amazon.com/waf/latest/developerguide/how-aws-waf-works-resources.html)

監査記録はactor sub・操作・対象ID・結果・時刻・request IDを保存する。token、署名付きURL、質問本文、原文、モデル応答を通常ログへ出さない。LangSmith追跡とBedrockの入力・出力ログも初期は無効とし、有効化する場合は送信・保持・アクセス範囲を明記する。

GitHub ActionsはOIDCのtrust policyを対象repo・Environmentに限定する。fork由来PRへAWS権限やsecretを渡さない。依存lockfile、Actionsのcommit SHA固定、secret検出、依存脆弱性検査、CDKの権限検査をCIに含める。devは削除可能、公開用はデータ保護と削除手順を明示する。CDK bootstrapとdeploy roleの権限もレビューする。

## 11. 公開前の検証

| 対象 | 必須の検証 |
| --- | --- |
| 認証・ロール | ID token、期限切れ、改ざん、別clientを拒否。userの管理API呼び出し、旧admin token、利用停止ユーザー、ログアウト済みtokenを拒否 |
| 所有者 | admin/userとも他ユーザーの会話・メッセージ・jobのID差し替えを拒否。不存在との応答差で情報を漏らさない |
| ファイル | 拡張子・Content-Type偽装、上限超過、破損・暗号化PDF、URL再利用、完了後の差し替え、不正key、再度completeを検証 |
| 非同期 | DB保存後の配送失敗、送信後のdispatcher停止、重複SQS、lease失効、model結果不明、DLQ回復を注入して状態と課金制御を確認 |
| 競合 | 二重送信、同一key別入力、同一会話の同時送信、取り込み中・生成中の文書削除、生成中の会話削除で復活や誤公開が起きない |
| RAG・表示 | 根拠不足、矛盾、追加質問、悪意ある文書、捏造citation、Markdown XSS、外部画像・危険URLを検証 |
| AWS・運用 | S3直接アクセス拒否、IAM過剰権限、CORS、no-store、CSP、上限到達時の停止、データ復旧、環境削除手順を確認 |

静的レビューとfakeテストだけで実AWSの検証完了とは扱わない。ステージごとにログを残し、成功した検証は変更・新しい懸念がない限り繰り返さない。

## 12. 着手時に確定する値

バックエンド言語と基盤の最終選定、repo名、リージョン、利用モデル、embedding次元数、月額予算、global/userの利用枠、MFAと招待方式、保持期間をADRに記録する。ここまでの数値は初期案であり、アカウントのサービス対応・課金見積もり・実測で調整する。

リポジトリ作成後の最初の検証は、モデル・S3 Vectors・Cognito group/access token・署名付きPOST/version固定・非同期job/outboxの成立確認とする。これを通してから画面と機能を広げる。
