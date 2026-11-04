# Frontend

Nuxt 4.6.2、Vue 3、TypeScript、Tailwind CSS 4のSPA。Node 24.22.0とpnpm 10.34.7を使い、依存はこのディレクトリの `pnpm-lock.yaml` に固定する。pnpm workspaceは使わず、FE単体で依存を管理する。

依存のinstallスクリプトは `package.json` の `pnpm.onlyBuiltDependencies` でesbuildだけ許可する。これは現在固定しているpnpm 10の設定形式。

## Nuxt 5への移行方針

Nuxt 4のまま `future.compatibilityVersion: 5` を有効にし、Nuxt 4で先行利用できるNuxt 5の既定動作を適用する。`compatibilityDate` は別の設定であり、Nuxtのメジャーバージョンを選ぶものではない。

画面・コンポーネント・composableは標準の `app/` 配下に置き、TypeScriptはNuxtが生成するproject referencesを使う。生成された `.nuxt/` の実装へ直接依存したり、独自の `baseUrl`・aliasで型解決を上書きしたりしない。

APIの業務処理はFastAPI、HTTPクライアントは `app/api/`、画面の通信状態はcomposableに分ける。現在はNuxtのserverルートを持たず、h3・NitroのAPIを直接使わない。将来serverルートを追加する場合は、Nuxt 4.6以降で利用できる公開APIの `nuxt/server` から明示的にimportする。

Nuxt更新時はlockfileを更新し、`mise run check:fe` と `mise run test:e2e` で型・静的生成・実HTTP通信を確認する。既存CIもこの互換設定を使う。今回の設定ではNuxt 5本体やNitro 3への移行は検証していない。理由と確認範囲は [ADR-0008](../docs/adr/0008-nuxt5-compatibility.md) を参照する。

## 起動

ツールのバージョンはルートの `mise.toml` と `mise.lock` で管理する。miseを導入し、リポジトリのルートで実行する。backendの起動手順は [Backend](../backend/README.md) を参照する。

```sh
mise trust mise.toml
mise install --locked
mise run setup
cp -n frontend/.env.example frontend/.env
mise run dev:fe
```

`http://localhost:3000` はfakeチャット、`http://localhost:3000/dev/connectivity` は接続テスト。接続先はNuxtのpublic runtime configで管理し、`NUXT_PUBLIC_API_BASE_URL` の既定値は `http://localhost:8000`。公開される設定なので認証情報を入れない。

## 型生成・検証・静的配信

```sh
mise run api:generate
mise run check:fe
mise run browser:install
mise run test:e2e
mise run api:check
```

BEを `mise run dev:be` で起動している間は、BEの起動時とPythonコード変更後の再起動時に型が自動更新される。BEを起動しない場合や単発で更新する場合は `mise run api:generate` を実行する。

`api:generate` はFastAPI → OpenAPI → openapi-typescriptの順で生成する。`app/api/client.ts` はopenapi-fetchに生成したpaths型を渡す。request、成功応答、422応答を生成型から推論し、HTTP契約を手書きで重複定義しない。

`check:fe` はNuxtの型検証、誤ったパス・必須項目欠落・数値message・存在しない応答フィールドを拒否する型テスト、通信中の重複防止の単体テスト、静的生成を実行する。

`test:e2e` は生成済みの `.output/public` と実backendを自動起動する。localhostの3000・8000番ポートを空けて実行する。既存のサーバーは流用しない。APIをmockせず、4種類の画面幅での送信、ドロワー、422、backend停止・再起動後の再送を確認し、終了時に起動プロセスを終了する。Linuxで初回実行する場合は `playwright install --with-deps chromium` を使う。

手動で静的生成物を確認する場合は、backendを起動したうえで次を別ターミナルで実行する。

```sh
mise exec -- uv run --directory backend python -m http.server 3000 --bind localhost --directory ../frontend/.output/public
```

静的配信では接続先設定は生成時に埋め込まれる。接続先を変更したら `NUXT_PUBLIC_API_BASE_URL` を指定して `mise exec -- pnpm --dir frontend generate` を再実行する。静的配信サーバーの起動時に環境変数を変更しても反映されない。

Playwrightのスクリーンショット・失敗時traceは `frontend/test-results/`、APIのE2Eログは `.logs/e2e-backend.log` に出力する。実機のキーボード、縦横表示、スクリーンリーダーは自動検証の対象外であり、未確認。

## 画面のビジュアル回帰テスト

月の振り返りの回答画面と、2件の引用元を開いた画面を390px・1280pxで比較する。正解画像は `tests/e2e/connectivity.spec.ts-snapshots/` に保存し、Gitで管理する。撮影時だけ確認日時を固定し、画像差分の許容閾値は設けない。

Dockerを起動してリポジトリのルートで実行する。スクリプトはPlaywright 1.64.1の公式Ubuntu NobleイメージをLinux amd64で使い、固定したmise・pnpm・uvの依存を導入し、静的サイトを生成して比較する。CIも同じスクリプトを実行する。Apple Siliconではamd64のエミュレーションを使う。

```sh
scripts/run-visual-tests.sh
```

画面を意図的に変更した場合は、同じ環境で正解画像を更新する。

```sh
scripts/run-visual-tests.sh --update-snapshots
```

更新後は6枚のPNGと `git diff --stat`・`git diff -- frontend/tests/e2e/connectivity.spec.ts-snapshots/` を確認し、想定した箇所だけ変わったことを確かめてからコミットする。PNGは画像ビューアでも新旧を見比べる。CIは正解画像を更新しない。失敗時の expected・actual・diff 画像とtraceは `frontend/test-results/` に保存し、CIでは `validation-results` artifactから確認する。

通常の `mise run test:e2e` は、実APIとの通信、入力、エラー、レスポンシブ動作を検証し、調査用の画面画像を `test-results/` に残す。`mise run check` はこの機能検証を含む。ビジュアル回帰テストは上記スクリプトで追加実行する。調査用画像は7日で消えるCI artifactであり、正解画像としては使わない。
