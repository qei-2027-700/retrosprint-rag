# 振り返り文書のデータ・接続・同期設計

状態：設計採用、未実装。[機能spec](../specs/reflection-retrieval.md)を利用者の動作・APIの正本とし、採用理由は[ADR-0012](../adr/0012-bigquery-aws-retrieval.md)に記載する。

## 上流契約と確認状態

2026年10月29日にgo-drive-etlのmain（`5a20988118edcf6beba40fbbf1134326b7f5012c`）の[公開文書](https://github.com/qei-2027-700/go-drive-etl/blob/5a20988118edcf6beba40fbbf1134326b7f5012c/docs/retro-documents.md)と[ViewのSQL定義](https://github.com/qei-2027-700/go-drive-etl/blob/5a20988118edcf6beba40fbbf1134326b7f5012c/iac/silver_gold.tf#L44)、[アクセス設計](https://github.com/qei-2027-700/go-drive-etl/blob/5a20988118edcf6beba40fbbf1134326b7f5012c/docs/retro-app-access.md)を確認した。以下は上流の文書とSQLに基づく対応であり、実環境のINFORMATION_SCHEMAや本文は今回取得していない。

Issue #8にある `etl_gold.reflection_documents` と `reflection_month` は旧名として扱う。現行の接続先は `etl_gold.retro_documents`、SQLの月条件は `retro_month = @month`。アプリ側の `reflection_month` へ変換する。デプロイ環境の移行確認が済むまで実接続を有効にしない。

| 上流の列・型 | アプリの項目 | NULL・変換・検証 |
| --- | --- | --- |
| `file_id` STRING | `document_id` | 非空・文書単位で一意を要求。不正・重複は契約違反として取得失敗 |
| `document_name` STRING | `document_name` | 上流はNULL可。表示時だけ「名称未設定」 |
| `drive_url` STRING | `drive_url` | 上流はNULL可。許可URL以外はリンクを出さない |
| `content` STRING | `content` | 非空を要求。上流チャンク順の結合本文。Drive原文そのものとは限らない |
| `content_version` STRING | `content_version` | 非空を要求。上流では元本文のSHA-256であり、結合本文のハッシュと比較しない |
| `retro_month` STRING | `reflection_month` | 上流はNULL可。月取得では一致行のみ、関連検索はNULLも許容 |
| `ingested_at` TIMESTAMP | `source_ingested_at` | UTCの時刻。同期日時と区別。NULLなら契約違反 |
| `retro_sequence` INTEGER | `sequence` | NULL可。表示順の補助にのみ使う |
| `retro_start_date` / `retro_end_date` DATE | `period_start` / `period_end` | NULL可。年月から補完せず、月条件にも使わない |

文書名・URL・年月・期間のNULL許容は上流文書で確認した。その他の列の実際のnullableモードと現行データの不変条件は接続検証で確認する。アプリが要求する非空条件と、BigQueryスキーマ上のREQUIREDは同義にしない。

Goldは通常Viewで、本文の永続コピーではない。元テーブルの期限切れに依存する。上流文書ではSandboxの最大60日期限が残る。上流の `content_version` が同じでも結合方式・メタデータの変更はあり得るため、AWSコピーは本文UTF-8のSHA-256 `body_digest` とメタデータのdigest、分割設定版も保持する。生成中に同一版で本文digestが変わった場合は利用を止め、再取り込みする。

### 月取得

```sql
SELECT file_id, document_name, drive_url, content, content_version,
       ingested_at, retro_month, retro_sequence, retro_start_date, retro_end_date
FROM `<configured-project>.<configured-gold-dataset>.retro_documents`
WHERE retro_month = @month AND file_id IN UNNEST(@authorized_file_ids)
ORDER BY retro_sequence, file_id
```

`@month` はSTRING、ID集合はARRAY<STRING>のパラメータとする。project・datasetはデプロイ設定で固定・検証し、リクエスト由来のSQL識別子を受けない。資料集合の許可IDはサーバー側で解決する。初期は小さな許可リストを対象にし、大規模化時は上流の認可情報と取得方式を再設計する。

月の扱いは日本時間の年月ラベルで、取り込み日時のUTC月や実期間の重複検索へ変換しない。JST月境界の直前・直後でも、同じ明示年月なら同じ条件になる。NULL月は月取得から除外し、資料集合内の月不明文書の有無は取得範囲の案内に表示する。月NULL確認のための追加クエリも同じ認可範囲・費用上限を使う。

## 責務と依存方向

```text
Nuxt → API handler（認証・入力検証・HTTP変換）
           → 質問usecase（用途分岐・認可・範囲・引用整合性）
                ├─ 月文書取得interface → BigQuery adapter
                ├─ 検索interface → Bedrock embedding / S3 Vectors adapter
                ├─ 文書利用可否interface → 許可集合・失効状態・元資料確認adapter
                ├─ 原文取得interface → BigQuery / S3 adapter
                └─ 回答生成interface → Bedrock adapter
管理者の同期コマンド → 取り込みusecase → BigQuery / S3 / Bedrock / S3 Vectors
```

APIはHTTPモデルから内部の質問・年月・利用者コンテキストへ変換する。usecaseはinterfaceとdomainだけに依存し、BigQuery row・Cognito claim・boto3の型を持ち込まない。mainで依存を組み立てる。既存Searchは質問だけを受けるため、用途・月・認可範囲を持つ検索条件へ拡張する。Generationには引用可能な根拠と取得範囲を渡す。月全文の入力と引用候補を分け、検索用Citationだけで月全文を表さない。

domainには取得文書・版・引用位置・利用可能状態・取得範囲を必要な分だけ追加する。APIでの取得と同期の両方が同じデータ変換・不変条件を使う。実装Issueの開始時に必要な配置だけ追加し、空のworker・repository等は作らない。

## 認証・認可

| 経路 | 認証・権限 |
| --- | --- |
| 利用者 → API | Cognito access tokenと現在の利用状態・アプリ側失効を検証。公開前に必須 |
| ローカル → Google Cloud | 明示した専用SAのimpersonationをADCで使用。個人認証への自動フォールバックなし |
| AWS → Google Cloud | WIF + 専用SA impersonation。AWS主体をアカウント・role等で限定し、信頼設定を検証 |
| API → AWS | 実行roleに必要なモデル推論、対象indexの検索、対象本文の読み取りだけを付与 |
| 同期 → AWS | 専用roleで対象本文・vectorの書込と削除、必要なモデル推論。API roleに同期権限を与えない |

WIFは[Google Cloudの公式手順](https://docs.cloud.google.com/iam/docs/workload-identity-federation-with-other-clouds)を基に、選んだ実行基盤で認証情報の取得・短期token更新・拒否条件を検証する。実行基盤は未選定であり、VM向け手順の存在だけでLambda等への適合を断定しない。

BigQueryの現行専用SAはjobUserとGold・上流3リソースの読み取り権限を持つ構成で、Rawの旧版本文にもアクセス可能である。通常Viewだけへの限定権限とは説明しない。上流の既存権限を無断で広げず、アプリへの公開範囲を確認する。クエリ実行project、dataset、locationを明示し、更新・削除・IAM管理権限がないことを検証する。

認証情報はサーバーのADC・実行roleで扱い、長期SA鍵やAWSアクセスキーを発行しない。設定例はbackend側に置き、FEへSQL・token・クラウド認証情報を渡さない。通常ログはrequest/job ID、状態、件数、遅延に限定する。本文・質問・回答・出典URL・生token・モデル入出力ログは初期無効とする。

利用者と資料集合の許可関係、文書の有効版、失効状態、削除世代はアプリ管理情報で保持する。PostgreSQLを採用するが具体テーブル・ORMは後続で定義する。サーバーが解決した資料集合を両経路へ適用し、検索時のmetadataフィルタだけに認可を任せない。生成前の元データ確認では版だけでなく本文・メタデータのdigestも照合し、変更があればその候補を除外する。S3 Vectorsの[metadata filtering](https://docs.aws.amazon.com/AmazonS3/latest/userguide/s3-vectors-query.html)は候補の絞り込みに使い、本文取得・生成前・原文応答前に現行状態を再検証する。

## 手動取り込み・更新・削除

初期は許可した合成資料集合を管理者コマンドで全件照合する。質問APIから取り込みを開始しない。成功した同期後24時間を検索の初期鮮度上限とし、超過時は503 `retrieval_failed` で同期を案内する。これは元資料の更新検知の保証時間ではない。定期実行は手動の再試行・復旧が成立してから別作業で追加する。

1. 実行ID・対象集合・設定版・開始時刻を記録し、同一集合の同期を直列化する。BigQueryの対象集合を正常に全件取得してmanifestを作る。取得途中の失敗や上限超過を「消えた文書」と判定しない。
2. `document_id + content_version + body_digest + metadata_digest + chunk_config_version + embedding_model_version` で取り込み世代を識別する。版だけで更新判定せず、同じ世代の再実行は完了段階から再開する。vector keyは世代とchunk位置から決定し、登録済みkeyをmanifestに保存する。
3. S3の非公開領域へ本文・metadataを保存し、固定したモデル・次元・分割条件でembeddingとvectorを登録する。metadataに資料集合・文書ID・版・取り込み世代・根拠位置を付ける。本文全体はvector metadataへ複製しない。
4. 件数・digest・原文位置を検証してから管理情報の有効世代を切り替える。切替は失効・削除世代を再確認して条件付きで行い、削除済み文書を再公開しない。古い候補は取得後にも除外する。新世代未完了時に旧版へ黙って戻さない。
5. 旧世代・未公開世代・削除対象の本文とvectorを削除する。失敗段階と残存keyを記録し、再試行する。本文削除とvector削除の両方を確認して物理削除完了とする。

外部サービスの一時障害は段階ごとに最大3回の指数バックオフで再試行し、上限後は失敗として管理者が再開する。embeddingの応答が不明な場合は自動再呼び出しせず、その段階を要確認にする。S3・vectorの再登録は固定keyで行い、モデルの再実行による二重課金が完全に防げるとは扱わない。

### 元資料の消失・権限変更

上流はDrive上の削除・移動を検知しておらず、Viewの行が残る場合がある。Gold行の存在やWIFの成功を、利用者が今も読める証明にしない。

初期の合成デモはサーバーの明示許可リストを正本とし、管理者が削除・許可変更を行う。個人資料を接続する前に、ETLから権限・削除イベントを受けるか、元資料の現在の権限・存在を照会する仕組みを別途設計・検証する。後者を選ぶ場合も、管理SAの閲覧可能性を利用者の権限と取り違えない。取得できない・不明なときはfail closedとし、私的資料の実接続を有効にしない。

全件照合が成功したmanifestから消えた文書は、先に利用停止・削除世代を更新し、次に非同期削除する。元テーブル期限切れ・取得権限拒否は同期失敗として公開を止め、全件消失として削除しない。明示削除・許可リストからの除外は即座に新規検索・原文取得・生成前の利用を止める。生成中に失効した文書を含む応答も返却前の再確認で破棄する。外部の変更を知るまでの遅延は別途残る。

### 本文保持

初期のAWSコピーは有効な現行世代だけを利用可能にし、旧世代・未完了世代・削除対象は24時間以内の物理削除を運用目標にする。削除に失敗しても利用停止を解除しない。24時間は実測や法的保持期限ではなく、実接続受入時に検証する目標値である。デモ終了時に合成資料の本文・vectorを削除する。

初期構成でS3 Versioning・バックアップ・複製を有効にする場合は、旧version・複製先も削除対象に追加し、保持期間を決めるまで個人資料を入れない。全文コピーを元データ期限後の保存手段にしない。保存済み会話の引用・監査・バックアップの即時消去はこの同期処理の対象外で、機能導入時に保持仕様を定める。原文表示はAPIを通し、初期は署名付きURLを発行しない。将来採用時は既存方針の最大2分と失効の限界を扱う。

## 費用・実接続の有効条件

BigQueryはdry runと `maximum_bytes_billed`（初期256 MiB/クエリ）を必須にする。月条件やLIMITだけで読み取り料金が減るとは扱わない。追加の版・NULL月確認もクエリ回数に含める。元データの期限・locationと、Google CloudからAWSへの越境転送の可否・費用を確認する。

Bedrockのembedding・生成、S3本文、vector保存・書込・検索、再試行、転送、ログの費用を分けて記録する。リージョン・モデル・次元・単価・想定文書量を確定して試算し、少量の合成資料で測定する。単価や予算を本設計から承認済みの数値として扱わない。

実接続設定は、日次の利用者別/全体の質問回数・token枠、同期の文書数・バイト数・embedding token枠、月次費用枠を必須にし、未設定ならliveを起動しない。初期の同時実行は質問1件・同期1件とし、同期と質問のモデル利用枠も共有する。呼び出し前に枠を予約し、結果不明の利用量は解放しない。予算通知だけで課金停止できるとは説明せず、アプリ停止フラグと呼び出し前の制限を設ける。実装時に利用量計測・競合・停止・再開を検証する。

## 外部環境の検証作業

| 検証 | 完了条件 |
| --- | --- |
| 上流の実スキーマ・移行 | View名・全列型/NULL・ID一意性・本文非空・版の意味・月境界/NULLを合成資料で照合。旧名を使わない |
| Google Cloud認証 | ローカルSA impersonationと選定AWS基盤のWIFを別々に検証。実行主体・短期token更新・信頼対象外の拒否・必要読取/不要更新権限を確認 |
| AWS | 選定リージョンのモデル・次元とS3 Vectors対応を確認し、APIと同期roleの許可/拒否、本文非公開・暗号化・ログ設定を確認 |
| データの安全性 | 利用者/文書ID差し替え、失効、同時削除、同期失敗、旧版候補、期限切れ、本文/vector残存の復旧を合成資料で確認 |
| 私的資料の接続前 | 元資料の削除・閲覧権限を確認する正本と経路を決定・検証し、不明時の利用停止を確認。未完了なら接続不可 |
| 実測 | 全文/検索の遅延・入力token・転送量・料金を条件とともに記録し、上限・停止・再開を確認 |

上流の専用SAによる月検索・権限検証の完了記録と、AWS基盤からの接続、本文・引用の正しさ、複数月での動作を区別する。本変更では外部環境へ接続・設定変更・課金検証を行っていない。

## 後続の独立作業

以下の独立した実装Issueを起票した。包括的な親Issueへの紐づけは行わず、本文書と必要な先行Issueだけを参照する。

| 作業 | 依存 | 成果・受入条件 |
| --- | --- | --- |
| [A. 用途別API・usecase・fake・FE（#9）](https://github.com/qei-2027-700/retrosprint-rag/issues/9) | 本設計 | 用途/月/範囲・状態のHTTP契約と生成型、全文取得interface、用途選択・範囲表示。既存fake互換と `mise run check` |
| [B. BigQuery adapterとローカル接続（#10）](https://github.com/qei-2027-700/retrosprint-rag/issues/10) | A | 実スキーマ/移行確認、パラメータ・NULL・費用上限・失敗の契約テスト。合成資料の実全文取得と原文取得を確認 |
| [C. 認証・文書認可・状態管理（#11）](https://github.com/qei-2027-700/retrosprint-rag/issues/11) | A | Cognito、資料集合、失効/削除世代と有効版の管理。ID差し替え・他者資料・生成中削除を拒否。外部公開前に必須 |
| [D. AWS基盤・接続認証（#12）](https://github.com/qei-2027-700/retrosprint-rag/issues/12) | 本設計 | AWSアカウント・region/モデル・CDK・IAM・WIF・利用枠/停止を整備。認証/課金なしの通常CIと分離して検証 |
| [E. 手動取り込みとAWS検索・生成（#13）](https://github.com/qei-2027-700/retrosprint-rag/issues/13) | B、D（共有環境はCも必須） | manifest・世代切替・重複排除・有限再試行・削除復旧。合成資料で実検索/生成と原文・引用を確認 |
| [F. 中間デモ・評価（#14）](https://github.com/qei-2027-700/retrosprint-rag/issues/14) | A、B、E（外部公開はCも必須） | specの正常/異常ケース、上限・鮮度・実測・残課題を記録。fake/mixed/liveを明示 |

BとDは準備を並行できる。認証未実装のB/Eはループバック上の合成資料検証に限り、複数人・私的資料・外部公開へ進めない。個人資料の削除・権限連携はCの受入条件に加えて別の実装作業として切り出す。
