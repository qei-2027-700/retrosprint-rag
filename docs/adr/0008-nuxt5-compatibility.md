# ADR-0008: Nuxt 4でNuxt 5の互換設定を使う

- 決定日：2026年10月18日
- 状態：accepted
- 関連：[ADR-0007](0007-openapi-client.md)

## 背景と選択肢

Nuxt 4で開発を進めながら、Nuxt 5への移行時に発生する変更を減らしたい。Nuxt 4の既定動作を維持する方法、Nuxt 5の開発版を導入する方法、Nuxt 4の公式互換設定を使う方法を比較した。

## 決定と理由

Nuxt 4.6.2と現在のlockfileを維持し、`future.compatibilityVersion: 5` を有効にする。Nuxt 4で先行利用できるNuxt 5の既定動作を、通常の開発とCIで継続して検証する。

この設定により、Vite Environment API、型付きページ、ページ名の正規化、厳密な副作用import検査などの既定値が変わる。変更を個別のフラグでNuxt 4の動作へ戻す設定は追加しない。今後問題が出た場合は、該当する設定と影響を確認して判断する。

標準の `app/` 配置とTypeScriptのproject referencesを維持する。画面は公開されたVue・Nuxt API、通信はOpenAPIから生成した型を使い、業務APIはFastAPIへ分離する。Nuxtの内部ファイルやh3・Nitroへの直接依存は追加しない。serverルートが必要になった場合は、Nuxt 4.6とNuxt 5の両方で使える `nuxt/server` の明示的なimportを基本とする。

## 影響と検証

互換設定を有効にした状態で、既存の `pnpm check:fe` と `pnpm test:e2e` を実行する。Nuxtの更新で互換設定の動作が変わる可能性もあるため、依存とlockfileの変更を同じ検証に通す。

2026年10月18日、互換設定を有効にした状態で型チェック・単体テスト1件・静的生成・実HTTPのE2E 8件が成功した。ログは `.logs/nuxt5-check-fe.log` と `.logs/nuxt5-e2e.log` に保存した。

このフラグだけではNitro 3などNuxt 5本体の変更は適用されない。Nuxt 5での動作や、将来導入するモジュールの互換性を確認済みとは扱わない。

## 再検討条件

Nuxt 5本体への更新時に、その時点の公式移行ガイドと導入済みモジュールを確認する。Nuxt 5への移行と、SSR・Nuxt serverルートの採用は別々に判断する。

## 参考

- [Nuxt 4.6.2のTesting Nuxt 5](https://github.com/nuxt/nuxt/blob/v4.6.2/docs/1.getting-started/18.upgrade.md#testing-nuxt-5)
- [Nuxt 4.6.2のMoving to nuxt/server](https://github.com/nuxt/nuxt/blob/v4.6.2/docs/1.getting-started/18.upgrade.md#moving-to-nuxtserver)
