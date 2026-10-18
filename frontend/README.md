# Frontend

Nuxt 4.6.2、Vue 3、TypeScript、Tailwind CSS 4のSPA。Node 24.22.0とpnpm 10.34.7を使い、依存はルートの `pnpm-lock.yaml` に固定する。

## 起動

リポジトリのルートで実行する。backendの起動手順は [Backend](../backend/README.md) を参照する。

```sh
pnpm install --frozen-lockfile
cp frontend/.env.example frontend/.env
pnpm dev:fe
```

`http://localhost:3000` を開く。接続先はNuxtのpublic runtime configで管理し、`NUXT_PUBLIC_API_BASE_URL` の既定値は `http://localhost:8000`。公開される設定なので認証情報を入れない。

## 型生成・検証・静的配信

```sh
pnpm api:generate
pnpm check:fe
pnpm --dir frontend exec playwright install chromium
pnpm test:e2e
pnpm api:check
```

`api:generate` はFastAPI → OpenAPI → openapi-typescriptの順で生成する。`app/api/client.ts` はopenapi-fetchに生成したpaths型を渡す。request、成功応答、422応答を生成型から推論し、HTTP契約を手書きで重複定義しない。

`check:fe` はNuxtの型検証、誤ったパス・必須項目欠落・数値message・存在しない応答フィールドを拒否する型テスト、通信中の重複防止の単体テスト、静的生成を実行する。

`test:e2e` は生成済みの `.output/public` と実backendを自動起動する。localhostの3000・8000番ポートを空けて実行する。既存のサーバーは流用しない。APIをmockせず、4種類の画面幅での送信、ドロワー、422、backend停止・再起動後の再送を確認し、終了時に起動プロセスを終了する。Linuxで初回実行する場合は `playwright install --with-deps chromium` を使う。

手動で静的生成物を確認する場合は、backendを起動したうえで次を別ターミナルで実行する。

```sh
uv run --directory backend python -m http.server 3000 --bind localhost --directory ../frontend/.output/public
```

静的配信では接続先設定は生成時に埋め込まれる。接続先を変更したら `NUXT_PUBLIC_API_BASE_URL` を指定して `pnpm --dir frontend generate` を再実行する。静的配信サーバーの起動時に環境変数を変更しても反映されない。

Playwrightのスクリーンショット・失敗時traceは `frontend/test-results/`、APIのE2Eログは `.logs/e2e-backend.log` に出力する。実機のキーボード、縦横表示、スクリーンリーダーは自動検証の対象外であり、未確認。
