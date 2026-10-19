# ADR-0010: uv同梱のPython build backendを使う

- 決定日：2026年10月19日
- 状態：accepted
- 関連：[ADR-0009](0009-mise-toolchain.md)

## 背景と選択肢

従来の `hatchling>=1.27,<2` とその推移依存は、分離されたビルド環境で `uv.lock` とは別に解決されていた。キャッシュなしのビルドでも外部パッケージを取得するため、同じコミットでもビルドに使うコードが変わり得る。

hatchlingと推移依存を制約ファイルで固定する方法と、固定済みのuvに同梱されたbuild backendを使う方法を比較した。現在のBEは標準のsrcレイアウトにある純粋なPythonパッケージで、独自のビルド処理を必要としないため、後者を採用する。

## 決定と影響

`build-system.requires` を `uv_build==0.8.15`、`build-backend` を `uv_build` とする。共通コマンド・CIでは、miseで固定したuv 0.8.15の同梱backendを使う。hatchling専用の設定を削除し、制約ファイルや開発用依存は追加しない。

`check:be` は `uv build --offline --no-cache` でsdistとwheelを生成する。build backendの外部取得やキャッシュへの依存が生じた場合は、この手順で検出する。これは配布物のビルドに対する制約であり、実行時・開発用依存のインストールは引き続き `uv.lock` を使う。

uvの更新時は `mise.toml`・`mise.lock` と `build-system.requires` を合わせて変更する。他のbuild frontendや異なる版のuvによる同梱backendの利用は保証しない。ネイティブ拡張や独自のビルド処理が必要になった場合は選定を見直す。

## 検証

キャッシュなし・オフラインでsdistからwheelまで生成できること、新しい環境への依存導入とimport、wheelに含まれるアプリコードと実行時依存定義が従来と同じであることを確認する。既存の `check:be` でlint・型・契約テストと、ソースツリー外へ導入したwheelのHTTP起動を確認する。

## 参考

- [uvの同梱build backend](https://docs.astral.sh/uv/concepts/build-backend/#bundled-build-backend)
