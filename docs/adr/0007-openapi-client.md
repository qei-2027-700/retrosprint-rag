# ADR-0007: FastAPIからNuxtのHTTP契約型を生成する

- 決定日：2026年10月18日
- 状態：accepted
- 関連：[Issue #2](https://github.com/qei-2027-700/retrosprint-rag/issues/2)

## 背景と選択肢

PythonのAPIとTypeScriptの画面でrequest・responseを重複定義すると、変更時に契約がずれる。PythonとTypeScriptで同じソースを直接読む方式、型の手書き、OpenAPIからの生成を比較した。

## 決定と理由

FastAPIのルートとPydanticモデルを正本とし、アプリの `openapi()` からJSONを出力する。openapi-typescript 7.13.0でpaths型を生成し、openapi-fetch 0.17.0でrequest・成功応答・422応答の型を推論する。小さな手書きクライアントにbase URLを渡し、HTTP契約型は追加しない。

OpenAPI・生成型はGit管理し、整列したJSONと明示したoperation IDで再生成を安定させる。通常CIは再生成後に生成先の追跡済み変更・未追跡ファイルを検出する。exportは明示的な開発用設定を使い、サーバー・DB・AWS・ローカルの `.env` に依存しない。

Nuxt 4.6.2、Vue 3.5.44、Tailwind CSS 4.3.3のViteプラグインを採用する。ランタイムはNode 24.22.0、Python 3.13.5、パッケージ管理はpnpm 10.34.7、uv 0.8.15とする。Nuxtの公開されたNode要件とパッケージ情報を確認し、Node 24を選んだ。解決した依存は各lockfileに固定する。

## 影響と検証

API変更時には再生成と生成物のコミットが必要になる。開発用の `mise run dev:be` は、Uvicornのリロードによる各プロセスの起動前に既存の生成タスクを実行する。独立した監視ライブラリは追加せず、生成失敗時はAPIの起動を止めてエラーを表示する。BEを起動せずに生成するコマンドとCIの生成差分検出は維持する。

静的SPAのAPI接続先は生成時に確定する。TypeScriptの型は実行時JSON検証を保証しないため、Pydanticの契約テストと実BEに接続するブラウザE2Eを併用する。

接続テストのためにrepository層やDB・AWSの空実装は追加しない。永続化の実装時には共通ルールのinterface分離を適用する。具体的な検証コマンドと確認範囲はルートと各アプリのREADMEに記載する。

## 再検討条件

別クライアントへの契約共有、SSE、実行時の応答検証が必要になった場合、生成物の配置とクライアントの責務を見直す。

## 参考

- [FastAPIのOpenAPI生成](https://fastapi.tiangolo.com/how-to/extending-openapi/)
- [openapi-fetchの生成型利用](https://openapi-ts.dev/openapi-fetch/)
- [Nuxt 4の導入条件](https://nuxt.com/docs/4.x/getting-started/installation)
- [Tailwind CSSのVite導入](https://tailwindcss.com/docs/installation/using-vite)
