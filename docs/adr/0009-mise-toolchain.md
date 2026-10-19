# ADR-0009: miseでツールと共通タスクを管理する

- 決定日：2026年10月19日
- 状態：accepted
- 関連：[ADR-0005](0005-github-actions-ci.md)、[ADR-0007](0007-openapi-client.md)

## 背景と選択肢

Node・Python・pnpm・uvのバージョン指定が、`.nvmrc`、`.python-version`、ルートの `package.json`、CI設定に分かれていた。利用者からmiseへの統一が指定されたため、ツールと共通タスクの管理を見直す。

既存の管理を維持する方法と、miseへ統一する方法を比較した。miseを追加する負担はあるが、BE・FEを横断するコマンドとツールの導入手順を一か所にまとめられる。

## 決定

ルートの `mise.toml` をツールのバージョンと共通タスクの定義元とする。Node 24.22.0、Python 3.13.5、pnpm 10.34.7、uv 0.8.15は変更しない。CIではローカルの検証に使ったmise 2026.3.7を固定する。

`.nvmrc`、`backend/.python-version`、ルートの `package.json` を取り除く。現在のJavaScriptアプリはFEだけなのでpnpm workspaceも取り除く。Nuxt固有のコマンドと依存は `frontend/package.json`、解決結果は `frontend/pnpm-lock.yaml` にまとめる。Pythonの依存と対応バージョンの範囲は `backend/pyproject.toml` で引き続き管理する。

ツールのURLとチェックサムは `mise.lock` に固定する。対応を検証するプラットフォームはmacOS arm64とCIのLinux x64とし、導入には `mise install --locked` を使う。ツール更新時は `mise.toml` を変更し、`mise lock --platform linux-x64,macos-arm64` でlockfileも更新する。生成されたlockfileは手編集しない。

共通入口を `mise run setup`、`mise run dev:be`、`mise run dev:fe`、`mise run api:generate`、`mise run check` とする。checkはBE・FE・生成差分・E2Eの順に実行し、失敗時は後続へ進まない。並列の依存タスクとして定義するとE2Eと静的生成が競合するため、順番を指定したrun stepsを使う。

`activate_aggressive` をプロジェクト内で有効にし、既存のnvm・pyenvのPATHが先頭にあっても、miseで選択したツールを優先する。uvにはmiseのPATH上の `python3` を使わせ、uvが別途ダウンロードしたPythonを優先しない設定とする。シェルの設定ファイルやグローバルなツール設定は変更しない。

## CIと検証

依存のinstallスクリプトの許可は、現在のpnpm 10が対応する `frontend/package.json` の `pnpm.onlyBuiltDependencies` で管理し、実際にpostinstallを使うesbuildだけにする。現在の `@tailwindcss/oxide` はinstallスクリプトを持たないため、許可一覧から除外する。

GitHub Actionsの個別のNode・pnpm・uv setupを、コミットSHAで固定した `jdx/mise-action` へ置き換える。同じ `mise.toml` と `mise.lock` を読み、`--locked` で導入する。インストール済みツールのキャッシュは無効にする。通常CIの権限とDB・AWS不要の方針は維持する。

ローカルではツール4種類の実行バージョン、`mise install --locked`、`mise run setup`、BE・FE・生成差分の検証が成功した。ログは `.logs/mise-install-locked.log`、`.logs/mise-setup.log`、`.logs/mise-check-be.log`、`.logs/mise-check-fe.log`、`.logs/mise-api-check.log` に保存した。起動中のサーバーとポートが重なるため、mise導入後のE2Eを含む全体検証は更新後のCIで確認する。Docker Compose対応は [Issue #4](https://github.com/qei-2027-700/retrosprint-rag/issues/4) で引き続き扱い、mise導入で完了したとは扱わない。

## 再検討条件

対応OSの追加時には、そのプラットフォームのlockfileエントリーと導入結果を確認する。コンテナのバージョン指定を追加するときもmiseとの整合を確認する。miseやツールの更新では既存の検証を実行し、変更をレビューする。

## 参考

- [miseのCI利用](https://mise.jdx.dev/continuous-integration.html)
- [miseのTOMLタスク](https://mise.jdx.dev/tasks/toml-tasks.html)
