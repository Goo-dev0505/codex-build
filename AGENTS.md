# AGENTS.md

このリポジトリでは、upstream の `codex-build` を変更せず、新しい `skills/fable/` 層を追加して拡張する。作業時の応答は日本語で行う。

## 正本

- フォルダ規約: `/Users/k.cross/Documents/README.md`
- アーキテクチャ: `docs/20260723_fable-design-review.md`
- 実行ループ: `skills/codex-build/SKILL.md`
- 計画形式: `skills/codex-build/references/plan-example.md`

矛盾がある場合は作業を止め、人間に確認する。設計の詳細をこのファイルへ重複転記しない。

## 役割とフェーズ

- Fable: Issue 分析、計画作成、人間の承認取得、実行後の受入条件レビュー。
- codex-build: 承認済み計画に従う実行のオーケストレーション、差分レビュー、テスト、コミット、証跡管理。
- Codex CLI: 実装、テスト、リファクタリングを含む product code と各タスクの成果物の作成。
- 人間: 計画、push／PR 作成、merge、危険な操作を承認する。

同一セッション内で Fable フェーズと codex-build フェーズを明確に分離する。Fable は codex-build 実行中に介入しない。product code とタスク成果物は必ず `codex exec` 経由で作成する。ただし、`skills/codex-build/SKILL.md` に定める既存の些末修正（5行以下）だけは同ルールの例外とする。

## 変更範囲

人間が将来の計画で明示的に承認しない限り、次を変更しない。

- `skills/codex-build/**`
- `.claude-plugin/**`
- `.codex-plugin/**`
- `README.md`
- `LICENSE`
- `THIRD_PARTY_LICENSES.md`

各タスクは計画に記載された正確なファイル allowlist だけを変更する。無関係な編集を混ぜない。削除、上書き、allowlist の拡張、作業スコープの拡大は、実行前に人間の明示承認を得る。

## ワークフローの不変条件

- 実行前に人間が承認した計画を必須とする。
- `1 Issue = 1 plan = 1 PR`、`1 task = 1 commit` とする。
- タスクは依存順に直列実行する。
- 各コミット前に必ず対象テストを実行し、失敗中はコミットしない。
- 1タスクで3回失敗したら `STOP` し、差分と診断を人間へ返す。実装を引き取らない。
- 再計画は、後続ターンで人間から明示指示を受けた後にだけ開始する。
- 実行状態の正本は `$GIT_DIR/codex-build/` 配下に永続化する。
- すべての `codex exec` に `< /dev/null` を付ける。開始前に pin 済みの model／effort を人間へ明示し、実行中に暗黙変更しない。
- sandbox や approval を迂回するオプションを使わない。

## Issue 取得

`gh` が利用可能なら `gh issue view` を使う。利用できない場合は、人間から Issue URL と本文を受け取ってから進める。`gh` を必須依存にしない。

## 検証

- Fable: `python3 -m unittest discover -s skills/fable/tests -v`
- 既存 codex-build: `python3 -m unittest discover -s skills/codex-build/tests -v`

変更に関係するテストを各コミット前に実行し、計画に追加のゲートがあればそれも実行する。

## Git

- コミットは Conventional Commits（`feat:`、`fix:`、`docs:`、`chore:` など）を使う。
- stage はタスクの正確な対象ファイルだけに限定し、`git add -A` を使わない。
- commit、PR、生成物に AI 帰属表記を追加しない。
- push または PR 作成の前に diff 要約を提示し、人間の明示承認を得る。
- force-push しない。

## 完了条件

次をすべて満たした場合のみ完了とする。

- scope check が green。
- 関連テストが green。
- diff をレビュー済み。
- テスト結果、判断、コミットなどの証跡を記録済み。
- 最終的な worktree の状態を人間へ報告済み。
