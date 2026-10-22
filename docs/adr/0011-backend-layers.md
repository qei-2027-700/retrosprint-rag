# ADR-0011: バックエンドのHTTP・業務処理・具体実装を分離する

- 決定日：2026年10月22日
- 状態：accepted

## 背景と選択肢

fakeチャットの初期実装では、質問のHTTPモデル、usecase、interface、fakeと合成資料を `questions.py` にまとめていた。usecaseの引数はinterfaceに依存していたが、戻り値はfake表示を含むHTTP応答モデルを兼ねていた。

機能単位で一つのモジュールを維持する案と、handler・usecase・interface・domain・adapterを分離する案を比較した。今後の実検索・モデル接続や評価からのusecase再利用を考え、後者を採用する。

## 決定と影響

HTTPのroute登録・handler・入力検証・応答変換は `api`、処理手順と処理結果は `application`、必要な外部機能のinterfaceは `application/ports.py`、引用・回答の業務データは `domain`、fake等の具体実装は `adapters` に置く。

domainの型は標準のdataclassで定義する。usecaseはdomainとinterfaceを参照し、FastAPI・Pydantic・具体adapterを参照しない。HTTPモデルは別に定義し、handlerで業務データから変換する。HTTPステータス、利用者向けエラーメッセージ、`mode: fake` はHTTP側に置く。

`main.py` はアプリ生成・設定・CORSと依存の組み立てを担当する。具体adapterをusecaseへ注入し、APIRouterを登録する。healthとechoもHTTP側へ移す。既存のパス・応答形式・開発用APIの有効条件は維持する。

今回の分離のためにDB用RepositoryやEntityの基底クラスは作らない。実際に利用する型・契約だけを定義する。

## 検証

HTTP契約テストに加え、HTTPとfakeを使わないusecase単体テストで、根拠不足時の生成省略、検索結果を使った生成、検索・生成の失敗伝播を確認する。既存の型検査・配布物検証・OpenAPI生成差分・実APIの画面E2Eを維持する。

## 再検討条件

実AWS接続、DB、認証・認可、非同期処理、評価の導入時に責務と型を見直す。変更後も業務処理へのHTTP・具体実装の依存を避け、実際の用途に合わせて分割する。
