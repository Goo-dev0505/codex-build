# Plan: <Issue を表す短い題名>

> Fable が作成し、人間が承認した後に codex-build へ渡す実装計画テンプレート。
> 山括弧の記入欄と例示値は、対象 Issue の具体的な情報へ置き換えること。
> 承認前は `Status: PENDING` のまま検証を失敗させ、実行へ進めないこと。

## Template basis

このテンプレートは、次の正本を参照している。

- [Fable MVP ブートストラップ計画](../../../docs/20260723_fable-mvp-plan.md)
- [Fable × codex-build 設計確認](../../../docs/20260723_fable-design-review.md)
- [codex-build plan example](../../codex-build/references/plan-example.md)

上記文書を読めない実行環境でも使えるよう、承認済み計画に必要な項目と
ガードレールは以下にすべて記載する。

## Approval

- **Status:** `PENDING`
- **Approver:** <承認した人間の名前または識別子>
- **Approval evidence:** <承認メッセージ、レビュー記録、または追跡可能な参照>
- **Approval date:** <YYYY-MM-DD>

人間の明示承認を得た後に限り、Status を `APPROVED` に変更し、承認者、証跡、
承認日を同時に記録する。Fable 自身を承認者にしてはならない。

## Issue / Source

- **Issue:** <https://github.com/OWNER/REPOSITORY/issues/NUMBER>
- **Source:** <Issue 本文、仕様書、または依頼への追跡可能な参照>
- **Repository:** <OWNER/REPOSITORY>

## Context

<現在の問題、実装する理由、利用者への効果、既知の前提を具体的に記載する。>

## Acceptance criteria

- <外部から検証可能な完了条件を1つ記載する。>
- <必要に応じて、期待結果と検証方法を追加する。>

## Branch & PR

- **Branch:** `<type>/<short-description>`
- **PR target:** `main`
- **PR unit:** `1 Issue = 1 plan = 1 PR`

## Model / Effort

- **Model:** `<run 全体で使用するモデル>`
- **Effort:** `<low|medium|high>`
- **Pinning:** run 開始時に固定し、実行中に暗黙変更しない。

## Risk

- **Level:** `<low|medium|high>`
- **Rationale:** <認証、課金、データ削除、秘密情報、外部公開などを含めて根拠を記載する。>

## Guardrails (things this plan bans)

- 各タスクは、そのタスクの **Files** に列挙した正確な repo 相対ファイルだけを変更する。
- allowlist の拡張、削除、上書き、スコープ拡大は、人間の明示承認なしに行わない。
- protected paths と、対象 Issue に無関係なファイルを変更しない。
- テストが失敗している間はコミットしない。
- AI 帰属表記を commit、PR、生成物へ追加しない。
- push・PR作成は、diff要約を提示して人間の明示承認を得た後にのみ行う。承認前は必ず停止する。

<対象固有の禁止事項、互換性制約、依存追加の可否を追加する。>

## Test commands (the gate)

- `python3 -m unittest discover -s <test-directory> -v`

すべての対象テストを各タスクのコミット前と最終ゲートで実行する。

## Tasks (ordered)

### T1 — <最初のタスク名>

- **Goal:** <このタスクだけで達成する単一の結果>
- **Files:** `path/to/exact-file.py`, `path/to/exact-test.py`
- **Constraints:** <変更禁止事項、公開インターフェース、互換性など、このタスク固有の制約>
- **Dependencies:** None
- **Tests:** `python3 -m unittest path.to.exact_test -v`
- **Completion criteria:** <テスト結果を含む、客観的に判定できる完了条件>

### T2 — <次のタスク名>

- **Goal:** <T1 の成果物を使って達成する単一の結果>
- **Files:** `path/to/another-file.py`, `path/to/another-test.py`
- **Constraints:** <このタスクの Files 以外を変更しないなどの固有制約>
- **Dependencies:** T1
- **Tests:** `python3 -m unittest path.to.another_test -v`
- **Completion criteria:** <客観的に判定できる完了条件>

必要な数だけ同じ6フィールドを持つタスクを追加し、見出し番号を T1 から欠番なく
連番にする。タスクは依存順に直列実行し、依存先には先行タスクだけを指定する。

## Out of scope

- <この計画で意図的に扱わない事項>

## Rollback

- fix-forward を基本とし、履歴を書き換えない。
- <対象固有の安全な復旧方針>

## Validation and handoff

1. 山括弧の記入欄を具体値へ置き換える。
2. `python3 skills/fable/scripts/validate_plan.py path/to/plan.md` を実行する。
3. 人間へ計画全体を提示し、明示承認を得る。
4. Approval の4項目を記録し、Status を `APPROVED` にして再検証する。
5. 検証成功後にだけ codex-build へ計画を渡す。
