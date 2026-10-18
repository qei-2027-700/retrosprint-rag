# ADR

重要な設計判断について、背景・選択肢・決定理由・影響・検証・再検討条件を残す。acceptedは採用済みを意味し、実装・検証の完了とは区別する。

| 番号 | 判断 | 状態 |
| --- | --- | --- |
| [0004](0004-aws-first-and-cdk.md) | AWS先行とAWS CDKの採用 | accepted |
| [0005](0005-github-actions-ci.md) | GitHub ActionsでCIを実行する | accepted |
| [0006](0006-postgresql.md) | アプリのDBにPostgreSQLを採用する | accepted |
| [0007](0007-openapi-client.md) | FastAPIからNuxtのHTTP契約型を生成する | accepted |
| [0008](0008-nuxt5-compatibility.md) | Nuxt 4でNuxt 5の互換設定を使う | accepted |

0004は移行元の番号を引き継いでいる。欠番を埋めるための文書は作らず、新規ADRは既存番号と重複しない番号で追加する。重要な判断を変更するときは新ADRから旧ADRへ置換リンクを付け、現行の仕様・構成書も更新する。
