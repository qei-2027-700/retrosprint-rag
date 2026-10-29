# ADR-0012: 月の全文取得はBigQuery、関連検索はAWSを使う

- 決定日：2026年10月29日
- 状態：accepted（設計の採用。実装・実接続は未完了）
- 対応：[Issue #8](https://github.com/qei-2027-700/retrosprint-rag/issues/8)

## 背景と選択肢

月全体の振り返りには対象月の全文が必要で、類似検索の上位だけでは網羅性を保証できない。一方、関連する経験の検索には、BedrockとS3 Vectorsの採用方針を生かす。

| 案 | 利点 | 課題 |
| --- | --- | --- |
| BigQueryに集約 | 取得元と版の管理をまとめられる | AWSでの類似検索とは別の構成・評価が必要 |
| AWSへ全用途を集約 | 回答時の取得先をAWSに揃えられる | 月全体の取得も同期の完了と鮮度に依存する |
| 用途別に併用 | 月の全文取得と類似検索の要件に合う | 二つの認証経路、版の差、同期と削除の管理が必要 |

## 決定

用途別の併用を採用する。FEはアプリのAPIだけを呼び、用途と対象月を明示する。質問文からの用途判定、両経路の自動合成、ETL独自HTTP APIは初期導入しない。

月の振り返りはBigQueryの文書Viewからパラメータ付きSQLで全文を取得する。関連検索はBedrock embeddingとS3 Vectorsを使い、本文はS3の版を固定したコピーから取得する。AWSへの取り込みは質問APIから独立させ、初期は管理者の手動実行とする。

AWS実行基盤からGoogle Cloudへの認証はWorkload Identity Federationと専用サービスアカウントのimpersonationを使い、長期鍵を発行しない。実行基盤・外部主体・信頼条件の確定と疎通は後続作業で行う。Google Cloudの[WIF](https://docs.cloud.google.com/iam/docs/workload-identity-federation)は鍵を使わない外部ワークロード認証を提供するが、本アプリでの動作は未確認である。

HTTP・業務処理・具体adapterの依存方向は[ADR-0011](0011-backend-layers.md)を維持する。詳細は[機能spec](../specs/reflection-retrieval.md)と[データ・接続・同期設計](../architecture/reflection-data.md)に記載する。

## 影響と検証

出典に文書ID・版・対象月・根拠箇所を保持する。AWS検索結果がBigQueryの現行版と異なる場合は回答に使わない。認可や現行版の確認に失敗した場合は取得失敗とし、根拠不足へ置き換えない。月全文をモデルへ収められない場合は生成せず、未処理の範囲を明示する。

上流の現行名称は `etl_gold.retro_documents` / `retro_month` であり、Issue本文の `reflection_documents` / `reflection_month` と異なる。アプリの `reflection_month` はadapterで対応づける。デプロイ済みリソースの状態は別途確認し、自動で旧名へフォールバックしない。

中間デモは合成資料だけを使い、BigQueryの実取得、手動取り込み、AWS検索・生成を段階的に検証する。ローカルfakeと実接続の結果は別々に記録する。AWSアカウント・資源の作成、課金を伴う接続検証は本設計変更に含めない。

## 再検討条件

月全文の量や遅延が同期APIの上限に収まらない場合は、階層要約・非同期ジョブを別途設計する。越境転送・費用・権限管理の負担が大きい場合はAWSへの集約を再比較する。上流の削除・権限情報を確認できない間は個人資料を接続しない。複数利用者へ展開する前に、文書公開範囲と分離方式を検証する。
