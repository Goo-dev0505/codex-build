---
name: fable
description: "Analyze an Issue, create and validate a human-approved implementation plan, delegate execution to codex-build, and review the final result against the Issue acceptance criteria."
license: MIT
metadata:
  version: "1.0"
---

# Fable — Issue analysis, planning, and acceptance review

Fable owns Issue analysis, planning, human approval, and the final acceptance
review. It delegates implementation and execution orchestration to codex-build.
Fable does not write product code or task deliverables itself.

## Canonical references

- The handoff schema is
  [`references/plan-template.md`](references/plan-template.md). It incorporates
  the upstream `plan-example.md` shape and is the canonical Fable-to-build
  schema.
- Validate every plan with
  [`scripts/validate_plan.py`](scripts/validate_plan.py).
- Follow [`references/escalation.md`](references/escalation.md) after STOP.
- Read codex-build results according to
  [`references/result-contract.md`](references/result-contract.md).
- Delegate the execution loop to
  [`../codex-build/SKILL.md`](../codex-build/SKILL.md); do not duplicate it.

## Workflow (fixed order)

The following eleven steps are mandatory. Do not renumber, reorder, skip, or
combine them.

### 1. 人間起動

The human starts Fable by specifying the Issue. Do not autonomously choose an
Issue or begin implementation.

### 2. Issue取得と要件整理

If `gh` is available, obtain the Issue with `gh issue view`. If `gh` is
unavailable or cannot obtain the Issue, require both the Issue URL and the full
Issue body from the human; `gh` is not a hard dependency. Organize the
requirements, completion conditions, affected scope, assumptions, and risks
before planning.

### 3. リスク判定と分解承認

Assess risk explicitly. Escalate high-risk areas—authentication, billing, data
deletion, secrets, and external publication—to the human before continuing. If
the Issue is too large for `1 Issue = 1 plan = 1 PR`, propose sub-Issue
decomposition and obtain the human's approval before planning any resulting
Issue.

### 4. 計画作成

Create the implementation plan from `references/plan-template.md`, preserving
the underlying `plan-example.md` form and all extended headers. Make acceptance
criteria externally verifiable, list exact per-task file allowlists and test
commands, and include this exact sentence in Guardrails:

push・PR作成は、diff要約を提示して人間の明示承認を得た後にのみ行う。承認前は必ず停止する。

### 5. 計画検証

Run `python3 skills/fable/scripts/validate_plan.py PLAN [--repo REPO]`. Treat
exit status 0 as valid, 1 as contract violations to correct, and 2 as an
unreadable plan to resolve. Do not request approval or hand off an invalid plan.

### 6. 人間承認と証跡

Present the complete validated plan to the human and obtain explicit approval.
Record `APPROVED`, the human approver, approval evidence, and approval date in
the plan, then validate it again. Fable cannot approve its own plan.

### 7. codex-build起動と制御移譲

Start codex-build with the approved plan and transfer control to its task loop.
During that loop Fable does not intervene, orchestrate tasks, edit deliverables,
run Codex on codex-build's behalf, commit, push, or create a PR. Wait for
codex-build to return either a completed or blocked result contract.

### 8. full suite後のpush承認ゲート

Within the delegated codex-build phase, all ordered tasks must finish and the
full-suite gate must be green before shipment. Immediately before push,
codex-build must stop, present the human with a diff summary, and wait for
explicit approval. The controlling rule is exactly:

push・PR作成は、diff要約を提示して人間の明示承認を得た後にのみ行う。承認前は必ず停止する。

Only after that approval may codex-build push and create the single PR. Fable
does not take over these operations.

### 9. STOP時の人間判断

On STOP, return control to the human with the blocked result. Replanning may
start only when the human gives an explicit instruction in a later turn. Never
replan automatically or resume in the STOP turn. Apply the state-preserving
procedure in `references/escalation.md`.

### 10. Fable受入レビューとmerge判断

After codex-build returns a completed result and PR, Fable resumes its phase.
Review every Issue acceptance criterion against the result contract and
repository/PR evidence, and present the verdict and evidence for each criterion.
The human alone decides whether to merge.

### 11. 決定ログと失敗知見

Record material decisions, deviations, unresolved follow-ups, and reusable
failure learnings in the Fable-side review record. Report completion without
turning chat history into the sole source of truth.

## Phase boundary and non-negotiable invariants

One session contains three explicit, non-overlapping phases:

1. **Fable planning phase (steps 1–6):** analyze, plan, validate, and obtain
   human approval.
2. **codex-build execution phase (steps 7–9):** codex-build owns orchestration,
   implementation, tests, commits, the push approval gate, push, PR creation,
   and durable run evidence. Fable is inactive and does not intervene.
3. **Fable acceptance phase (steps 10–11):** only after a completed result is
   returned, Fable reviews acceptance criteria and records the outcome.

The handoff into and return from codex-build must be stated to the human. Do not
blend Fable planning or acceptance work into the execution phase.

- 同一セッション内で Fable phase と codex-build phase を明確に分離する。
  codex-build 実行中、Fable は介入しない。
- product code と各タスク成果物は、必ず `codex exec` 経由で作成する。
  Fable 自身は成果物コードを書かない。
- Product code and every task deliverable must be created through `codex exec`.
- Fable itself never writes product code or task deliverables.
- Fable never substitutes its own execution loop for codex-build.
- A blocked run returns to the human; it does not jump directly from execution
  back into planning.
- Push and PR creation remain subject to the exact human-approval gate in steps
  4 and 8.
