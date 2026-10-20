# ADR-0011: BEのローカル開発にDocker Composeを使う

- 決定日：2026年10月20日
- 状態：accepted
- 関連：[Issue #4](https://github.com/qei-2027-700/retrosprint-rag/issues/4)、[ADR-0009](0009-mise-toolchain.md)、[ADR-0010](0010-bundled-python-build.md)

## 背景と選択肢

Issue #4はBE・FEのCompose化を提案していたが、今回の実装範囲はユーザーの指定によりBEだけとする。ホストで両方を起動する既存手順を維持し、Python・uvのホスト導入なしでBEを動かす選択肢を追加する。

FEもコンテナ化して起動時の自動型生成を維持する方法と、BEだけをコンテナ化して生成を明示的に実行する方法を比較し、後者を採用する。BEにNode・pnpm・miseとFE依存を追加せず、既存のFE環境を使う。

## 決定と影響

ルートの `compose.yaml` にbackendだけを定義する。Python 3.13.5 slim-bookwormとuv 0.8.15の公式イメージをmulti-platform digestで固定し、既存のmise設定とbuild backendに合わせる。依存は `uv sync --locked` で導入し、manifestとlockfileの不整合も検出する。開発用イメージには検証用依存も含める。本番用イメージとしては扱わない。

uvicornのfactoryを直接起動し、`src/` と `scripts/` のbind mountでリロードする。仮想環境は `/opt/venv` に置き、ホストの `.venv` を持ち込まない。manifest・lockfileの変更は再ビルドで反映するため、依存用の永続volumeは作らない。ビルドcontextはbackendに限定し、`.dockerignore` で必要な入力だけを許可する。

コンテナ内では `0.0.0.0:8000`、ホストでは `127.0.0.1:8000` に限定する。`.env` は実行時の `env_file` として読み、イメージには含めない。ブラウザの接続先はlocalhost、CORSのoriginはホストFEの `http://localhost:3000` とする。

OpenAPIの出力ディレクトリだけを共有し、既存のexportスクリプトをコンテナで実行する。TypeScript型はホストのFEコマンドで生成する。Composeでは起動・リロード時の自動生成を行わず、API変更後の明示的な生成を開発手順とする。既存の `mise run dev:be` の自動生成とCIの生成差分チェックは維持する。

## 検証と再検討条件

新しいcheckout相当で、設定検証・ビルド・health・docs・echo・CORS・リロード・停止と再起動・OpenAPI出力を確認する。API未変更時の生成差分と既存の共通検証も確認し、実行結果は手順書に記録する。

FEのコンテナ化や自動型生成が必要になった場合は、Node依存の配置と生成物の共有方法を再検討する。実行基盤と本番向けイメージは別の判断とする。

## 参考

- [uvのDocker連携](https://docs.astral.sh/uv/guides/integration/docker/)
