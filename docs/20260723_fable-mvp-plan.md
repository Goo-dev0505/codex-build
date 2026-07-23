# Plan: Fable MVP ブートストラップ

> 本書は、Fable MVP を実装するための承認済み codex-build 入力計画である。
> codex-build は、以下の順序付きタスク、ファイル allowlist、ガードレール、
> テストゲートに従って実行する。

## Approval

- Status: `APPROVED`
- Approver: 人間（KITAcore）
- Approval evidence: user message `"OK! すすもう"`
- Approval date: `2026-07-23`

## Issue / Source

- Issue: このリポジトリにおける Fable MVP bootstrap
- Source: `docs/20260723_fable-design-review.md` の §9「Codex への実装計画」
- Repository: `fable-orchestrator`

## Context

このリポジトリは、upstream の codex-build を変更せず、新しい
`skills/fable/` 層を追加して拡張する。Fable は Issue 分析、検証可能な受入条件を
含む計画作成、人間の承認取得、実行後の受入条件レビューを担当する。
codex-build は承認済み計画を受け取り、依存順にタスクを直列実行し、Codex CLI に
実装させ、スコープ検査、diff レビュー、テスト、コミット、実行証跡管理を担当する。

MVP では Fable フェーズと codex-build フェーズを同一セッション内で明確に分離する。
Fable は計画が承認された後に codex-build へ制御を渡し、codex-build 実行中には
介入しない。実行が STOP した場合は必ず人間へ返し、再計画は人間が後続ターンで
明示的に指示した場合にのみ開始する。

## Acceptance criteria

- Fable から codex-build へ渡す計画テンプレートが、設計レビュー §5 の全必須項目と
  push 承認ゲートを備え、バリデータで機械検証できる。
- バリデータは適正な計画を PASS とし、必須項目、タスク単位の正確なファイル宣言、
  テストコマンド、承認記録、push 承認ガードレールの不備を FAIL とする。
- Fable スキルが設計レビュー §4 の11ステップを定義し、同一セッション内の
  フェーズ分離、codex-build 実行中の非介入、Codex CLI による成果物作成、
  STOP 後の人間判断、後続ターンでの明示的な再計画を強制する。
- 再計画時は失敗 run の状態を削除せず、`current` ポインタを安全に退避または
  rename してから、新しい run-id と明示した base で再開できる。
- `/fable:run <issue番号>` 相当の起動コマンドが、利用可能な場合は
  `gh issue view` を使い、利用できない場合は Issue URL と本文を人間へ要求する。
  `gh` をハード依存にしない。
- コマンド定義は実行ループを重複実装せず、`skills/fable/SKILL.md` を正本として
  委譲する。
- `FABLE.md` がインストール方法と upstream 保守手順を説明し、manifest の変更を
  必要としない。
- 全タスクで scope check が green となり、指定された2つのテストコマンドが
  コミット前および最終ゲートで green となる。

## Branch & PR

- Branch: `codex/fable-bootstrap`
- PR target: `main`
- PR unit: この MVP bootstrap の1計画につき1 PR

## Model / Effort

- Model: `gpt-5.6-sol`
- Effort: `high`
- Pinning: run 開始時に固定し、実行中に暗黙変更しない。

## Risk

- Level: `low`
- Rationale: 変更は新規の Markdown、Python バリデータ、unittest に限定され、
  upstream の codex-build、plugin manifest、既存 README、ライセンス、および
  外部公開・認証・課金・データ削除・秘密情報を扱うコードには触れないため。

## Guardrails (things this plan bans)

- 次の protected paths は変更しない:
  - `skills/codex-build/**`
  - `.claude-plugin/**`
  - `.codex-plugin/**`
  - `README.md`
  - `LICENSE`
  - `THIRD_PARTY_LICENSES.md`
- 各タスクは、そのタスクの **Files** に列挙された repo-relative な正確な
  ファイル allowlist だけを変更する。allowlist の拡張、他タスクのファイル、
  本計画ファイル `docs/20260723_fable-mvp-plan.md`、その他の無関係なファイルを
  変更しない。
- product code および各タスク成果物は、必ず `codex exec` 経由で作成する。
- Fable フェーズと codex-build フェーズを同一セッション内で明確に分離し、
  codex-build 実行中に Fable は介入しない。
- AI 帰属表記を commit、PR、生成物へ追加しない。
- push・PR作成は、diff要約を提示して人間の明示承認を得た後にのみ行う。承認前は必ず停止する。

## Test commands (the gate)

- `python3 -m unittest discover -s skills/fable/tests -v`
- `python3 -m unittest discover -s skills/codex-build/tests -v`

両コマンドを各タスクのコミット前と全タスク完了後に実行する。いずれかが失敗して
いる間はコミット、push、PR 作成を行わない。

## Tasks (ordered)

### T1 — 計画スキーマ + バリデータ

- **Files:** `skills/fable/references/plan-template.md`,
  `skills/fable/scripts/validate_plan.py`,
  `skills/fable/tests/test_validate_plan.py`
- **Depends on:** なし
- **Do:** Fable から codex-build へ渡す計画テンプレートとバリデータを実装する。
  テンプレートは設計レビュー §5 の必須フィールド、すなわち Issue リンク、
  Context、検証可能な受入条件、Branch & PR、Guardrails、Test commands、
  Tasks（各タスクの Files、Do、Depends on、Done when）、モデル、effort、
  リスクレベルと根拠、承認記録（status、承認者、承認証跡、承認日）を含む。
  Guardrails には本計画と同一の push 承認ゲート定型文を含める。
  バリデータは、必須フィールド、各タスクの repo-relative な正確なファイル宣言、
  1件以上のテストコマンド、承認記録、push 承認ガードレールを検査する。
  unittest には完全な正例と、必須フィールド欠落、タスクのファイル宣言欠落または
  不正、テストコマンド欠落、承認記録欠落、push 承認ガードレール欠落の各負例を
  含める。
- **Done when:** `plan-template.md` が設計レビュー §5 の全必須フィールドと
  push 承認ゲート定型文を持ち、バリデータが正例を PASS、各欠陥例を FAIL とし、
  T1 の positive / negative unittest と両テストゲートがすべて green である。

### T2 — Fable スキル本体

- **Files:** `skills/fable/SKILL.md`,
  `skills/fable/references/escalation.md`,
  `skills/fable/references/result-contract.md`,
  `skills/fable/tests/test_skill_contract.py`
- **Depends on:** T1
- **Do:** Issue 分析から受入判定と報告までを担う Fable スキルを実装する。
  `skills/fable/SKILL.md` に次の11ステップを順序どおり定義する。
  1. 人間が Issue を指定して起動する。
  2. `gh` が利用できる場合は `gh issue view` で Issue を取得し、利用できない
     場合は人間から Issue URL と本文を必須入力として受け取り、要件、完了条件、
     影響範囲、リスクを整理する。
  3. リスクを判定し、高リスク領域は人間へエスカレーションする。大きすぎる
     Issue はサブIssue分解を提案し、人間の承認を得る。
  4. `plan-example.md` 形式と拡張ヘッダーに従って計画を作成し、Guardrails に
     push / PR 承認ゲート定型文を記載する。
  5. `validate_plan.py` で計画を検証する。
  6. 人間の計画承認を取得し、承認記録を計画へ残す。
  7. codex-build を起動し、そのタスクループ中は Fable が介入しない。
  8. 全タスクとフルスイートの完了後、push 直前で停止し、diff 要約を人間へ
     提示して、明示承認後にのみ push と PR 作成を行う。
  9. STOP 時は必ず人間へ返し、再計画は人間が後続ターンで明示的に指示した
     場合にのみ開始する。
  10. Fable が Issue の受入条件に対する最終レビューと根拠提示を行い、人間が
      merge を判断する。
  11. 決定ログと失敗知見を記録して完了する。

  同一セッション内で Fable と codex-build のフェーズを明確に分離し、
  codex-build 実行中に Fable が介入しないこと、product code と各タスク成果物を
  必ず `codex exec` 経由で作成することを不変条件として記載する。
  `escalation.md` は「STOP → 人間へ返す → 人間の後続ターンでの明示指示 →
  再計画」の順序を固定する。再計画前に失敗 run と部分コミットを確認し、base と
  その扱いを明示する。既存の `$GIT_DIR/codex-build/current` は削除せず、
  一意な退避名へ archive / rename して現在ポインタを安全に退役させ、既存の
  `runs/<run-id>/` を一切削除せず保存する。その後に新しい run-id を採番する。
  `result-contract.md` は run.md、tasks.md、interfaces.md、blocked 時の diff と診断、
  完了報告、Fable の受入条件レビューに必要な入力と出力を定義する。
  `test_skill_contract.py` は11ステップ、フェーズ分離、非介入、
  `codex exec` 不変条件、STOP 後の順序、削除を伴わない run-state 退役手順を
  契約テストで検証する。
- **Done when:** `SKILL.md` に全11ステップ、同一セッション内のフェーズ分離、
  codex-build 実行中の Fable 非介入、product / task 成果物の `codex exec` 経由が
  明記され、`escalation.md` に STOP 後の固定順序と `current` の archive / rename、
  新 run-id、base、部分コミットの扱い、state を決して削除しない手順があり、
  `result-contract.md` が codex-build から Fable への結果契約を定義し、
  T2 の契約テストと両テストゲートがすべて green である。

### T3 — 起動コマンドと結線

- **Files:** `commands/fable.md`,
  `FABLE.md`,
  `skills/fable/tests/test_command_contract.py`
- **Depends on:** T2
- **Do:** `/fable:run <issue番号>` で Issue 取得、分析、計画作成、検証、人間承認
  までを起動するコマンド定義を実装する。引数がない場合は Issue 指定を要求する。
  `gh` が PATH 上に存在する場合は `gh issue view` を使い、存在しない場合または
  利用できない場合は人間に Issue URL と本文を要求して処理を続行し、`gh` を
  ハード依存にしない。コマンドは実行ループを複製せず、
  `skills/fable/SKILL.md` に委譲する。コマンド定義の frontmatter は必要な
  `Bash`、`Read`、`Write`、`AskUserQuestion` を許可する。
  `FABLE.md` はシンボリックリンクを用いたインストール方法と、upstream を
  取り込む保守手順を説明する。導入または保守のために plugin manifest を
  変更しない。`test_command_contract.py` は frontmatter、引数なし時の要求、
  `gh issue view` と fallback、`gh` 非依存、`SKILL.md` への委譲、ガイドの
  インストール / upstream 保守契約を検証する。
- **Done when:** `commands/fable.md` が引数なし時に Issue 指定を要求し、
  `gh` が利用できる場合は `gh issue view` を使用し、利用できない場合は
  Issue URL と本文を要求して続行し、`skills/fable/SKILL.md` を正本として
  委譲する。`FABLE.md` に manifest を変更しないインストール方法と upstream
  取り込み手順が記載され、T3 の契約テストと両テストゲートがすべて green である。

## Out of scope

- タスク単位のモデルルーティング
- 並列実行
- 複数コーダー対応
- Issue の自動 merge
- Issue の自動 triage
- メトリクス収集

## Rollback

- fix-forward のみとする。
- 履歴を書き換えない。rebase、reset、amend、force-push によって完了済み
  タスクの履歴を修正せず、必要な修正は新しいタスクと新しい commit で行う。
