# ADR-0005: GitHub ActionsでCIを実行する

- 決定日：2026年10月18日
- 状態：accepted（workflow実装済み。GitHub Actions上の実行は未確認）
- 関連：[開発計画 #1](https://github.com/qei-2027-700/retrosprint-rag/issues/1)

## 背景

GitHubで管理するモノレポで、frontend・backend・IaC・API契約の変更を継続的に確認したい。CodexまたはClaude Codeによる変更も、同じコマンドと判定基準で検証する。本人からGitHub Actionsを利用したいという指定があった。

## 選択肢

| 選択肢 | 利点・負担 |
| --- | --- |
| GitHub Actions | PR・コミットと検証結果をまとめて確認できる。workflowと実行時間・権限を管理する必要がある |
| ローカル実行のみ | CIの設定は不要だが、検証漏れを防ぎ、PRごとの結果を共有する運用が必要になる |
| 別のCIサービス | 利用できるが、今回のGitHub管理に加えて接続・設定の管理が必要になる |

## 決定

GitHub ActionsをCIに採用し、workflowを `.github/workflows/` に置く。初期整備中はmainへの直接pushを認め、branch作成・PRを必須にしない。通常CIはmainへのpushを対象とし、PRを使う場合も検証する。各プロジェクトの実行コマンドが用意できた段階から追加する。存在しないコマンドや、チェック対象がなく常に成功するworkflowを先に作らない。

| 対象 | 通常CIで行う検証 |
| --- | --- |
| frontend | 型チェック、テスト、SPAのbuild |
| backend | lint、型チェック、unit/contractテスト、外部接続不要のintegrationテスト |
| API契約 | FastAPIのOpenAPI出力、TypeScript型生成、コミット済み生成物との差分確認 |
| IaC | CDKのテスト、AWS接続を必要としないsynth |

ローカルとCIで同じコマンド・lockfileを使う。Pythonはuv、Node系はpnpmを使い、ランタイム・依存・利用するActionsの版を導入時に固定する。外部Actionsはcommit SHAで固定し、更新時に確認する。

通常CIではAWS認証やBedrockの呼び出しを必要としない。CDKのアカウント情報参照などで実AWS接続が必要になる検証は別のworkflowへ分ける。実AWSの接続検証・品質評価は課金を伴うため、対象環境・実行者・利用枠を決めたうえで明示実行する。

AWSデプロイの自動化は後続で設計する。初期の実行契機は手動を候補とし、mainへのpushだけで自動デプロイする方針はまだ確定しない。AWS接続にはOIDCを使い、長期アクセスキーをGitHub Secretsへ保存する構成を前提にしない。対象repo・branchまたはEnvironmentをIAMの信頼条件で制限し、必要なjobだけに `id-token: write` を与える。

通常CIの `GITHUB_TOKEN` は `contents: read` を基本とし、fork PRにAWS権限やsecretを渡さない。未信頼のPRコードを権限付きで実行しない。必要な権限はjob単位で追加する。

## 影響とトレードオフ

検証結果をPR・コミットに対応付けて確認できる。workflow、実行時間、キャッシュ、依存更新を管理する作業が増える。CIの利用枠・料金は実行構成を決めて確認し、無料・無制限とは扱わない。

通常CIの成功だけでRAG品質・AWS接続・デプロイの成功とは判断しない。それぞれの検証結果を分ける。branch・PR運用と必須チェック・branch保護の導入は、初期整備が進みworkflowが動作した段階で見直す。

## 検証方法と現在の結果

2026年10月18日、Issue #2で `.github/workflows/ci.yml` と共通の `pnpm check` を実装した。新しいcheckoutからのローカル実行は成功し、型不一致・生成差分・APIテスト失敗の検出を確認した。GitHub Actions上での実行と成功は未確認。CDK・AWSの検証はまだ組み込んでいない。

次のmainへのpushまたはPRでは、GitHub Actions上でも通常CIの成功を確認する。AWSを使うworkflowでは対象環境の制限・最小権限・停止条件を確認する。

## 再検討条件

実行時間・利用枠・必要な実行環境が要件を満たさない場合は、job分割やrunner、別サービスを比較する。自動デプロイへ変更する場合は実行条件と環境保護を別の判断として残す。

## 根拠

2026年10月18日の本人指定と、既存の通常CI・課金対象評価を分離する方針。

AWSへのOIDC認証と権限設定は [GitHub公式資料](https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-in-aws) を参照する。
