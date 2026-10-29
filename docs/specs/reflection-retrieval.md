# 月の振り返り・関連する経験の検索

状態：設計採用、未実装。[Issue #8](https://github.com/qei-2027-700/retrosprint-rag/issues/8)の成果物。[ADR-0012](../adr/0012-bigquery-aws-retrieval.md)、[データ・接続・同期設計](../architecture/reflection-data.md)を参照する。現在の実装は[単一質問のfake版](chat-question.md)のままとする。

## 用途と操作

利用者が「月の振り返り（`monthly_reflection`）」「関連する経験の検索（`related_search`）」を選ぶ。月の振り返りは年月必須、関連検索は年月を任意の絞り込みに使う。質問文による自動切り替えは行わない。「先月」などの自由入力は受けず、年月選択で `YYYY-MM` を送る。日本時間での現在月・前月の選択補助はFEが確定した年月を表示して行う。

両方を求める場合は用途ごとに送信する。APIは選択された用途だけを処理し、回答に用途・対象月・取得範囲を表示する。資料で答えられない質問は根拠不足とする。資料内の命令はデータとして扱い、一般チャットへの切り替えは行わない。

月の振り返りは認可された対象月の全文を取得し、top-kで代用しない。年月ラベルの一致を対象とし、実際の期間の重複や、その月のすべての出来事を網羅するとは説明しない。年月NULLの文書は月取得の対象外。対象月が空なら別月を推測して補わない。

## 要求契約

`POST /api/questions` を拡張する。以下は実装前の設計例で、実装時はFastAPIからOpenAPI・TypeScript型を生成する。

```json
{"question":"この月の成果と悩みを整理して","retrieval_mode":"monthly_reflection","reflection_month":"2026-09"}
```

```json
{"question":"相談のタイミングで悩んだ経験は？","retrieval_mode":"related_search","reflection_month":null}
```

| 項目 | 条件 |
| --- | --- |
| `question` | strictな文字列。前後空白除去後1〜2,000文字。既存上限を維持 |
| `retrieval_mode` | `monthly_reflection` / `related_search`。新FEは必須で送る |
| `reflection_month` | 実在する年月の `YYYY-MM`（0001〜9999年）。月の振り返りは必須、関連検索は省略・NULL可 |
| その他 | 未定義項目、任意SQL、文書ID、所有者ID、外部接続先の指定は422で拒否 |

互換期間は `retrieval_mode` 省略を `related_search` と解釈し、既存の質問だけの要求を維持する。既存の `mode: fake` は実行方式として残し、用途に転用しない。実接続を有効にしても認証不要の開発用APIを公開しない。fakeでは現在の代表質問と失敗ケースを保ち、用途別の合成ケースを追加する。

## 応答と出典

月の振り返りの成功例（設計例）を示す。

```json
{
  "status":"answered",
  "mode":"live",
  "retrieval_mode":"monthly_reflection",
  "reflection_month":"2026-09",
  "answer":{"text":"早めに相談できたことが成果です。[c1]","citation_ids":["c1"]},
  "citations":[{
    "id":"c1","document_id":"synthetic-2026-09","document_name":"2026年9月の振り返り",
    "content_version":"synthetic-v1","reflection_month":"2026-09",
    "heading":"成果","page":null,"quote":"早めに相談できた。",
    "original_text":null,"drive_url":null,
    "locator":{"start":0,"end":9}
  }],
  "coverage":{
    "scope":"month_documents","complete":true,"omitted":false,
    "documents_retrieved":1,"documents_used":1,
    "checked_at":"2026-10-29T00:00:00Z","last_sync_at":null
  }
}
```

`mode` は `fake` / `live` / `mixed`。`mixed` は一部adapterがfakeの検証時に限り、画面と検証記録でどの段階がfakeかを明記する。公開デモでfakeを実回答と表示しない。

`coverage.scope` は月取得で `month_documents`、関連検索で `search_matches`。`complete: true` は対象月の取得文書全文を生成入力に含めた場合だけとし、関連検索では常にfalse。`documents_used` は生成入力に含めた文書数で、引用文書数とは分ける。関連検索は上位最大5箇所の探索であり網羅性を示さない。`checked_at` は元データの版・利用可否を確認した時刻、`last_sync_at` はAWS側の成功した公開処理の時刻で、月取得ではNULL。

回答の `citation_ids` は必ず返した出典を指す。出典と引用を業務層で検証し、不整合なら生成失敗とする。`locator` は取得本文に対するUnicodeコードポイント単位の半開区間で、`content[start:end] == quote` を満たす。ページや見出しを確定できなければNULLとし、捏造しない。元のDriveファイルの座標とは扱わない。

既存fakeの `original_text` は保持する。実接続では原文全体を質問応答へ重複添付せずNULLとし、`GET /api/documents/{document_id}/versions/{content_version}` で再認可した版の本文・文書名・対象月を取得する。応答は `Cache-Control: no-store`。旧版・失効・削除は404、現行版確認の障害は503とする。月取得はBigQuery、関連検索は再検証後のS3コピーを使い、更新後に同じ版の原文を取得できなければ「この版は確認できません」と表示する。Driveリンクは補助であり、版を固定した原文表示の代わりにしない。

`document_name` NULLは「名称未設定」、`drive_url` NULLはリンク非表示。URLを返す場合はHTTPSの `drive.google.com` だけを許可する。本文・回答・引用はテキスト表示としHTMLを実行しない。

## 状態・エラー・上限

200では `answer` / `citations` / `coverage` を常に返す。非回答状態は `answer: null`、`citations: []` とし、説明を `message` で返す。

| HTTP / status・code | 条件と画面の扱い |
| --- | --- |
| 200 `answered` | 回答と出典・取得範囲を表示 |
| 200 `no_documents` | 月の認可済み文書が0件。対象月を変える案内 |
| 200 `insufficient_evidence` | 取得・検索成功後、質問に答える根拠が不足 |
| 200 `stale_evidence` | 検索候補はあるが現行版との不一致で全件除外。同期を待つ案内 |
| 200 `input_limit_exceeded` | 月全文が上限超過。生成せず `coverage.complete: false, omitted: true, documents_used: 0` と取得件数を返す。「全文を処理できません」と表示 |
| 401 `unauthenticated` | tokenなし・不正。再ログインを案内 |
| 403 `access_denied` | 認証済みでも用途・資料集合の権限がない。資料の存在を明かさない |
| 422 入力検証 | FastAPI標準detail。入力を保持して修正 |
| 429 `usage_limit_exceeded` | アプリの利用枠・同時実行上限。再送を抑止 |
| 502 `generation_failed` | 生成失敗・引用不整合。回答として表示しない |
| 503 `retrieval_failed` | BigQuery・AWS・認可情報の取得失敗、サービス主体の権限拒否、全対象を正常取得できない場合。根拠不足にしない |
| 504 `processing_timeout` | 全体の処理期限超過。自動再送しない |

非200の業務エラーは `{ "code": "retrieval_failed", "message": "資料を取得できませんでした。", "request_id": "opaque-id" }` の形式とし、内部のSQL・資源名・本文を含めない。既存fakeの500 `question_processing_failed` はfake専用として維持する。

月全文は最大50文書・UTF-8本文合計1 MiB・生成入力合計20,000 tokenを初期のアプリ上限とする。質問・指示・引用識別情報を含めて生成モデルのコンテキストと出力枠に収まるかも事前確認する。文書数・バイト上限超過を検知したら読み取りを打ち切り、取得件数はその時点の下限としてmessageで説明する。黙って先頭だけを要約しない。全文取得後のtoken超過でも生成しない。分割要約は後続設計とする。

関連検索は検索候補最大20箇所から認可・現行版を確認して最大5箇所を使う。すべての候補が古ければ `stale_evidence`、候補がないか認可対象に根拠がなければ `insufficient_evidence`。BigQueryでの版確認はID集合のパラメータ付き一括取得とする。生成入力上限は同じ20,000 tokenで、超過する根拠箇所を除外した場合は `coverage.omitted: true` を表示する。

同期APIのBE全体期限は60秒、FEは65秒とする。現在のfakeの10秒設定は拡張時に変更する。月取得の再試行は期限内の一時障害に限り最大2回、生成の結果不明時は自動再生成しない。送信中の重複送信防止・失敗時の入力保持・新しいチャットのリセットは維持する。これらは設計上限であり、測定済みの速度・品質を意味しない。

## 権限と利用条件

APIでCognito tokenと現在の利用状態を検証し、usecaseへ利用者の内部ID・資料集合の権限を渡す。BigQueryのサービスアカウント権限と利用者の閲覧権限は分ける。文書ID・版・URLの指定でも認可を迂回できない。検索前の資料集合フィルタに加え、検索後・生成前・原文返却前にも現在の状態を確認する。

初期の実接続デモは専用の合成資料集合を固定し、ループバック上で本人が操作するローカルAPIを対象とする。未認証状態では私的資料や共有ネットワークに公開しない。外部公開はCognito・認可の受入条件を満たしてから行う。管理者ロールだけで私的文書を読める設計にはしない。

## 中間デモと受入条件

| ケース | 検証する結果 |
| --- | --- |
| 合成資料2件を同月に置き「この月の成果と悩みを整理して」 | 月の実BigQuery全文取得。両方を生成入力に含め、回答・引用・件数を照合 |
| 別月の合成資料も置き「相談のタイミングで悩んだ経験は？」 | 手動取り込みした実AWS検索・Bedrock生成。文書ID・版・引用を照合 |
| 月指定なし・不正月・両用途を含む質問 | 入力検証と、選択用途だけを処理することを確認 |
| 文書なし・根拠不足・旧版・上限超過 | 表の状態、生成の実行有無、範囲表示を確認 |
| 権限拒否・ID差し替え・元サービス障害・タイムアウト | 情報漏えいなく拒否し、障害を根拠不足と表示しない |

デモは段階を分ける。まず用途別fakeでAPI・FEと失敗状態を検証し、次に合成資料のBigQuery実取得を生成fakeで確認する。最後に手動AWS取り込み・実検索・実生成を確認する。未達の段階はfakeまたは未実装と明示し、実接続デモ完了とはしない。

受入時はOpenAPI・型生成、usecase・adapter契約テスト、APIとFEのE2Eを更新し、`mise run check` を通す。認証・課金なしの通常CIと、実接続・品質・費用の検証を分ける。月全文の取得確認、検索結果の引用整合性、更新・削除後の利用停止を合成資料で検証し、コード・資料・モデル・設定の版と検証範囲を記録する。
