# 共通skill

リポジトリ固有のskillは `<skill-name>/SKILL.md` と必要な補助ファイルをここへ配置する。現時点では独自skillは未作成。

Codex用の `.agents/skills` とClaude Code用の `.claude/skills` は、どちらもこのディレクトリへの相対シンボリックリンクにする。共通の規則は [開発ルール](../rules/development.md) を参照する。

リンクがない環境では、リポジトリのルートで次を実行する。既存の同名ファイル・ディレクトリは上書きしない。

```sh
mkdir -p .agents .claude
ln -s ../docs/skills .agents/skills
ln -s ../docs/skills .claude/skills
```

Codexは `.agents/skills` を探索し、シンボリックリンクを扱う。[OpenAI公式資料](https://learn.chatgpt.com/docs/build-skills)

Claude Codeはプロジェクトの `.claude/skills` を探索し、リンクされたskillを扱う。追加後は利用するバージョンで検出を確認する。[Claude Code公式資料](https://code.claude.com/docs/en/skills)
