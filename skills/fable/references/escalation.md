# STOP escalation and replanning contract

This contract applies whenever codex-build returns a blocked result or reaches
its three-failed-iterations STOP condition. Its order is fixed:

## 1. STOP

Freeze the execution attempt. Do not invoke another `codex exec`, change the
plan, modify task output, rewrite commits, push, or create a PR. Capture the
stopping task, current diff, failure output, diagnosis, completed and partial
commits, and the failed run-id from the result contract.

STOP must not trigger automatic replanning. Fable must not restart the run in
the same turn.

## 2. 人間へ返す

Return control to the human. Present the stopping task, diff, diagnosis, test
evidence, failed run-id, partial commits, and safe decision options. Preserve
the worktree and all durable state while waiting; do not silently repair or
discard either one.

## 3. 人間の後続ターンでの明示指示

Wait for the human to give an explicit replanning instruction in a later turn.
Silence, a status question, or the original execution approval is not
replanning approval. Do not resume in the STOP turn, and do not infer permission
to expand scope, rewrite history, discard partial commits, or choose a new base.

## 4. 再計画

Only after step 3 may Fable begin a new planning phase. Perform these actions in
order:

1. Read the failed run's `run.md`, `tasks.md`, `interfaces.md`, allowlists, STOP
   report, and current repository diff. Inspect every completed and partial
   commit before selecting a base.
2. State the exact new base commit or ref and explicitly record how each partial
   commit is handled: retained in the base, superseded by a later fix-forward
   task, or intentionally excluded in a separate preserved worktree. Never
   reset, amend, or otherwise rewrite completed history.
3. Resolve `$GIT_DIR` for the current worktree. Preserve
   `$GIT_DIR/codex-build/runs/<run-id>/` in place; no run directory or file
   within it may be deleted, truncated, or reused.
4. Retire `$GIT_DIR/codex-build/current` without deleting it. Atomically rename
   it to a unique archive name such as
   `current.archived.<UTC-timestamp>.<old-run-id>`. Confirm the destination does
   not already exist; if it does, choose another unique name. This is an
   archive/rename operation, not removal or overwrite.
5. Create and validate a new plan that records the selected base, the treatment
   of partial commits, the replacement scope, and the human's new approval
   evidence.
6. Only after the old `current` pointer is retired and the new plan is approved,
   allocate a fresh, never-reused run-id. codex-build then creates a new
   `runs/<new-run-id>/` and a new `current` pointer under its normal preflight.

The invariant is:

`STOP → 人間へ返す → 人間の後続ターンでの明示指示 → 再計画`

There is no STOP-to-replan shortcut, automatic retry, same-turn restart, or
state deletion path.
