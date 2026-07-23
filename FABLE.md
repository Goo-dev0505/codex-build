# Fable の導入と保守

Fable はこのリポジトリに追加した計画・受入レイヤーであり、
upstream codex-build を直接改造しない。実体の正しい配置場所は次のとおり。

- リポジトリ:
  `/Users/k.cross/Documents/10_Apps/fable-orchestrator`
- 起動コマンドの実体: `commands/fable.md`
- スキルの実体: `skills/fable/`

導入では実体をコピーせず、ユーザー設定からこの2つへシンボリックリンクを
張る。これにより、リポジトリを安全に更新すれば導入先にも同じ内容が反映される。

## インストール

以下は Claude Code のユーザー設定 `~/.claude` に
`/fable:run <issue番号>` を導入する手順である。まずリポジトリ位置とリンク先を
確認する。

```bash
FABLE_REPO=/Users/k.cross/Documents/10_Apps/fable-orchestrator
CLAUDE_CONFIG_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
COMMAND_LINK="$CLAUDE_CONFIG_DIR/commands/fable/run.md"
SKILL_LINK="$CLAUDE_CONFIG_DIR/skills/fable"

test -f "$FABLE_REPO/commands/fable.md"
test -f "$FABLE_REPO/skills/fable/SKILL.md"

for destination in "$COMMAND_LINK" "$SKILL_LINK"; do
  if [ -e "$destination" ] || [ -L "$destination" ]; then
    printf 'STOP: link destination already exists: %s\n' "$destination"
    exit 1
  fi
done
```

`-e` は既存ファイルまたはディレクトリを、`-L` は切れたリンクを含む既存の
シンボリックリンクを検出する。どちらかに該当した場合は上書きしない。既存物の
所有者と用途を確認し、人間が別名への退避を承認するまで停止する。

事前確認が通った場合だけ、親ディレクトリとリンクを作成する。

```bash
mkdir -p "$CLAUDE_CONFIG_DIR/commands/fable" "$CLAUDE_CONFIG_DIR/skills"
ln -s "$FABLE_REPO/commands/fable.md" "$COMMAND_LINK"
ln -s "$FABLE_REPO/skills/fable" "$SKILL_LINK"
```

`ln -sf` は使わない。既存パスの削除、置換、上書きは行わない。

## 動作確認

リンクが意図した実体を指すことを確認する。

```bash
test -L "$COMMAND_LINK"
test -L "$SKILL_LINK"
readlink "$COMMAND_LINK"
readlink "$SKILL_LINK"
test -f "$COMMAND_LINK"
test -f "$SKILL_LINK/SKILL.md"
```

Claude Code を再起動し、テスト用リポジトリで次を実行する。

```text
/fable:run 123
```

引数なしの `/fable:run` が Issue 指定を要求することも確認する。`gh` がない、
未認証、または Issue 取得に失敗する環境では、Issue URL と完全な本文の入力を
求め、その入力後に計画作成へ進めば正常である。

## 削除しない更新方針

リンク先はリポジトリ内の実体なので、通常の更新でリンクを張り直す必要はない。
リンクまたは既存パスを削除・上書きして更新してはならない。リンク先が誤って
いる場合や競合する既存物がある場合は停止し、人間の承認後に既存物を一意な
別名へ退避してから新しいリンクを作る。退避物は履歴として保持する。

## upstream codex-build の保守

保守では Fable 層と upstream codex-build の境界を守る。plugin manifest の変更は
導入にも更新にも不要であり、`.claude-plugin/**` と `.codex-plugin/**` の変更は
禁止する。`skills/codex-build/**`、`README.md`、`LICENSE`、
`THIRD_PARTY_LICENSES.md` も保護対象であり、ローカルの独自修正を加えない。

### 1. upstream remote を確認する

```bash
FABLE_REPO=/Users/k.cross/Documents/10_Apps/fable-orchestrator
git -C "$FABLE_REPO" remote -v
git -C "$FABLE_REPO" remote get-url upstream
```

`upstream` が未登録なら、URLを人間と確認してから一度だけ追加する。

```bash
git -C "$FABLE_REPO" remote add upstream https://github.com/cathrynlavery/codex-build.git
git -C "$FABLE_REPO" remote get-url upstream
```

既存の `upstream` が別URLを指している場合は書き換えず、停止して人間へ報告する。

### 2. fetch して差分をレビューする

```bash
git -C "$FABLE_REPO" fetch upstream
git -C "$FABLE_REPO" log --oneline --left-right --cherry-pick HEAD...upstream/main
git -C "$FABLE_REPO" diff --stat HEAD...upstream/main
git -C "$FABLE_REPO" diff --name-status HEAD...upstream/main
git -C "$FABLE_REPO" merge-tree \
  "$(git -C "$FABLE_REPO" merge-base HEAD upstream/main)" \
  HEAD upstream/main
```

コミット内容、変更パス、競合候補を確認する。特に
`commands/fable.md`、`FABLE.md`、`skills/fable/**`、`docs/**`、
`AGENTS.md` への upstream 側の変更や競合が見えたら統合せず停止する。

### 3. 保護対象を守って統合する

取得した upstream 差分を正確に列挙した保守計画を作り、人間の明示承認を得る。
作業用ブランチで upstream コミットを履歴ごと統合し、upstream の
`skills/codex-build/**` をローカル仕様へ直接編集しない。

```bash
git -C "$FABLE_REPO" switch -c chore/sync-codex-build-YYYYMMDD
git -C "$FABLE_REPO" merge --no-ff upstream/main
```

Fable 所有パスとの競合、manifest の変更要求、または保守計画の allowlist 外変更が
発生した場合は、競合を推測で解消せず停止して人間へ返す。manifest を Fable 用に
拡張する対応は禁止する。

### 4. 両テストと最終差分を確認する

```bash
cd "$FABLE_REPO"
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s skills/fable/tests -v
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s skills/codex-build/tests -v
git diff --stat upstream/main...HEAD
git diff --name-status upstream/main...HEAD
git status --short
```

両テストが green で、scope と差分が承認済み保守計画に一致するまで push しない。
差分要約、テスト結果、競合対応、保護対象の確認結果を人間へ提示し、push の明示承認
を得る。承認後に限り `git push` を実行する。PR 作成も同じ明示承認の対象であり、
force-push は行わない。
