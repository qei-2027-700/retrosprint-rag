# Backend

Python 3.13.5、uv 0.8.15を使う。FastAPI、Pydantic、uvicornなどの解決済みバージョンは `uv.lock` に固定している。DB・AWS・認証情報は起動、テスト、型生成に不要。

## 起動

リポジトリのルートで実行する。

```sh
uv sync --directory backend --frozen
cp backend/.env.example backend/.env
pnpm dev:be
```

`http://localhost:8000/health` と `http://localhost:8000/docs` を利用できる。`pnpm dev:be` はbackendを作業ディレクトリとし、そこにある `.env` を読む。

| 変数 | 既定値・用途 |
| --- | --- |
| `RETROSPRINT_ENABLE_DEV_API` | `false`。ローカルの `.env.example` では `true` にしてechoを有効化 |
| `RETROSPRINT_CORS_ORIGINS` | `["http://localhost:3000"]`。JSON配列で許可するoriginを完全一致指定 |

公開向け設定では `RETROSPRINT_ENABLE_DEV_API=false` とする。echoはルートとOpenAPIの両方から除外される。healthはプロセスのHTTP応答だけを確認する。CORSは認証・認可を提供しない。

## 検証と契約出力

```sh
pnpm check:be
pnpm api:generate
pnpm api:check
```

`check:be` はruff lint・format、mypy、pytest、sdist/wheelのビルド、wheelの導入・HTTP起動を順に実行する。wheel検証はソースツリー外の一時環境へ配布物を導入し、healthの200とechoの404を確認して終了する。

`api:generate` は `scripts/export_openapi.py` からアプリを構築し、開発用APIを含むOpenAPIとTypeScript型を出力する。起動済みサーバーへアクセスせず、開発用APIとCORS設定を明示して `.env` に依存しない契約を出力する。生成物は手編集しない。変更後は生成物もコミットする。

HTTP契約の正本は `src/retrosprint_rag/main.py` のルートとPydanticモデル。期待動作と受入条件は [接続テスト仕様](../docs/specs/dev-connectivity.md) を参照する。
