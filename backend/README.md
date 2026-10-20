# Backend

Python 3.13.5、uv 0.8.15を使う。FastAPI、Pydantic、uvicornなどの解決済みバージョンは `uv.lock` に固定している。DB・AWS・認証情報は起動、テスト、型生成に不要。

ビルドにはuv 0.8.15同梱の `uv_build` を使い、`pyproject.toml` でも同じ版を完全固定する。`check:be` のビルドは `--offline --no-cache` で実行し、外部のビルド依存や既存キャッシュを必要としないことを確認する。uvを更新するときはbuild backendの版も同時に更新する。理由と検証範囲は [ADR-0010](../docs/adr/0010-bundled-python-build.md) を参照する。

## 起動

### Docker ComposeでBEを起動

Docker EngineとCompose v2を用意し、リポジトリのルートで実行する。ホストのPython・uv・Node・pnpm・miseはBEの起動に不要。

```sh
cp -n backend/.env.example backend/.env
docker compose config --quiet
docker compose up --build
```

`http://localhost:8000/health` は200、`http://localhost:8000/docs` はSwagger UIを返す。APIの `/` にはルートを設けていないため404となる。コンテナ内では `0.0.0.0:8000` でlistenし、ホストには `127.0.0.1:8000` だけを公開する。

`backend/.env` をComposeの `env_file` から渡す。`.env.example` は開発用echoを有効にし、ホストで起動するFEの `http://localhost:3000` をCORSで許可する。環境変数を変更したら `docker compose up -d --force-recreate` で反映する。

Python 3.13.5 slim-bookwormとuv 0.8.15の公式イメージを、版とmulti-platform digestで固定する。依存は `uv.lock` を検証する `uv sync --locked` で導入する。更新時は `mise.toml`・`mise.lock`・build backendとの整合を保ち、Dockerfileの版とdigestも更新する。

`src/` と `scripts/` だけを読み取り専用でbind mountし、Pythonコードの保存でuvicornがリロードする。仮想環境はイメージ内の `/opt/venv` に置き、ホストの `.venv` と共有しない。ビルド入力は `.dockerignore` で限定し、ローカルの `.env`・キャッシュ・認証情報をイメージへ送らない。

別のターミナルから状態・ログを確認し、停止できる。

```sh
docker compose ps
docker compose logs --tail=100 -f backend
docker compose down
```

バックグラウンド起動は `docker compose up --build -d --wait`。依存を変えた場合は再ビルドする。更新するパッケージ名は必要なものに置き換える。

```sh
# uv.lockをホストへ書き戻す（ホストのuvは不要）
docker compose run --rm --no-deps --volume "$(pwd)/backend:/workspace" --workdir /workspace backend uv lock --upgrade-package fastapi
docker compose up --build -d --wait
```

`pyproject.toml`・`uv.lock`・Dockerfile・testsはイメージに取り込むため、変更後の反映には再ビルドが必要。テストは `docker compose run --rm --no-deps backend pytest` で実行できる。

### ComposeのBEとホストのFEを接続

FEを使う場合は、ホストにmiseとFE用ツールを導入してからルートで実行する。BE用の `mise run dev:be` は同時に起動しない。

```sh
mise trust mise.toml
mise install --locked node pnpm
mise exec -- pnpm --dir frontend install --frozen-lockfile
cp -n frontend/.env.example frontend/.env
mise run dev:fe
```

ブラウザは `http://localhost:3000`、API URLは `http://localhost:8000` を使う。`backend` はCompose内部のサービス名であり、ホストのブラウザには指定しない。FEのHMRは既存のホスト開発サーバーが行う。

ComposeのBEはFastAPIのfactoryを直接起動し、起動・リロード時の型生成は行わない。API変更後は次の順でOpenAPIとTypeScript型を更新する。OpenAPIだけならDockerだけで生成できる。TypeScript型にはホストのNode・pnpmが必要。

```sh
docker compose run --rm --no-deps backend python scripts/export_openapi.py
mise exec -- pnpm --dir frontend api:generate
git diff -- frontend/openapi/openapi.json frontend/app/api/generated/schema.d.ts
```

OpenAPIの出力先だけをホストの `frontend/openapi/` と共有する。生成時は `.env` に依存せず開発用APIを有効にする。APIを変更していなければ、コミット済みの生成物から差分は出ない。

### ホストでBEを起動

ツールのバージョンはルートの `mise.toml` と `mise.lock` で管理する。miseを導入し、リポジトリのルートで実行する。

```sh
mise trust mise.toml
mise install --locked
mise run setup
cp -n backend/.env.example backend/.env
mise run dev:be
```

`http://localhost:8000/health` と `http://localhost:8000/docs` を利用できる。`mise run dev:be` はbackendを作業ディレクトリとし、そこにある `.env` を読む。

起動時と `src/`・`scripts/` 内のPythonコード変更後の再起動時に、OpenAPIとFEの型を自動生成する。FEの依存導入も必要なため、先に `mise run setup` を実行する。生成に失敗した場合はサーバーを起動せず、エラーをターミナルへ出力する。修正・保存すると再起動時に再試行する。

| 変数 | 既定値・用途 |
| --- | --- |
| `RETROSPRINT_ENABLE_DEV_API` | `false`。ローカルの `.env.example` では `true` にしてechoを有効化 |
| `RETROSPRINT_CORS_ORIGINS` | `["http://localhost:3000"]`。JSON配列で許可するoriginを完全一致指定 |

公開向け設定では `RETROSPRINT_ENABLE_DEV_API=false` とする。echoはルートとOpenAPIの両方から除外される。healthはプロセスのHTTP応答だけを確認する。CORSは認証・認可を提供しない。

## 検証と契約出力

```sh
mise run check:be
mise run api:generate
mise run api:check
```

`check:be` はruff lint・format、mypy、pytest、sdist/wheelのビルド、wheelの導入・HTTP起動を順に実行する。wheel検証はソースツリー外の一時環境へ配布物を導入し、healthの200とechoの404を確認して終了する。

`api:generate` は `scripts/export_openapi.py` からアプリを構築し、開発用APIを含むOpenAPIとTypeScript型を出力する。起動済みサーバーへアクセスせず、開発用APIとCORS設定を明示して `.env` に依存しない契約を出力する。生成物は手編集しない。変更後は生成物もコミットする。

HTTP契約の正本は `src/retrosprint_rag/main.py` のルートとPydanticモデル。期待動作と受入条件は [接続テスト仕様](../docs/specs/dev-connectivity.md) を参照する。

## Composeの検証記録

2026年10月20日、macOS arm64、Docker Engine 28.0.4、Compose v2.34.0で確認した。ローカルcloneに今回の差分を適用した一時checkoutを使い、既存の `.venv`・`node_modules`・`.env` を持ち込まずに開始した。

1. `.env.example` をコピーし、`docker compose config --quiet`、`docker compose build --no-cache`、`docker compose up --no-build -d --wait` が成功した。実行コマンドと結果は `.logs/compose-validation.log`、一時checkoutの場所は `.logs/compose-checkout.txt` に保存した。
2. health・docsの200、ルートの404、echoの空白除去と200・422、CORSの許可・拒否、echo無効時の404とOpenAPIからの除外を確認した。ソースへ一時的にルートを追加し、リロード後の200と復元後の404を確認した。停止時の通信失敗、再起動後のecho再送も成功した。
3. コンテナ内のpytestは14件成功した。仮想環境が `/opt/venv` にあり、ホストの `.venv` と `.env` がコンテナの作業ディレクトリに存在しないことを確認した。依存更新用mountは絶対パスを使い、`uv lock --check` が成功した。
4. コンテナからOpenAPIを出力し、一時checkoutへFE依存を `pnpm install --frozen-lockfile` で導入してTypeScript型を生成した。`git diff --exit-code -- frontend/openapi/openapi.json frontend/app/api/generated/schema.d.ts` で差分なしを確認した。
5. 既存の `mise run check` ではBEのlint・型・14テスト・配布物検証、FEの型・1テスト・静的生成、生成差分検証が成功した。E2EはComposeとのポート競合で一度失敗したため、Composeを停止して `mise run test:e2e` を再実行し、8件成功した。ログは `.logs/check.log` と `.logs/e2e-retry.log`。既存のCI定義は変更していない。実AWSは未検証。

同日、起動済みのホストFEとComposeのBEをChromeで接続し、health成功、echo応答と空白除去、BE停止時の通信エラーと入力保持、再起動後の再送成功を確認した。画像とJSONの検証記録は `.logs/evidence/20261020-2140-compose-*`、BEログは `.logs/compose-browser-backend.log` に保存した。確認後もFE・BEは起動した状態で残した。
