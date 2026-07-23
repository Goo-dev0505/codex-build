# codex-build to Fable result contract

This contract defines the evidence codex-build returns and the acceptance-review
record Fable produces. Chat summaries are convenient views, not canonical
state.

## Sources of truth

- Execution state is canonical under
  `$GIT_DIR/codex-build/runs/<run-id>/`. The run directory is immutable
  evidence after completion or STOP and must remain available for review.
- The approved plan is the source of truth for Issue scope, acceptance criteria,
  guardrails, test gates, and approval evidence.
- The Fable-side plan and acceptance-review record are the source of truth for
  planning decisions, human approvals, criterion verdicts, and final decision
  logs.
- Repository commits, the final diff, test outputs, and the PR are primary
  implementation evidence referenced by the records above.

## Required execution files

### `run.md`

`run.md` must identify the run-id, plan path and content hash, Issue, branch,
base, pinned model and effort, tracker, start/end status (`completed` or
`blocked`), final commit when available, full-suite evidence, push-approval
status and evidence, and PR URL when one exists. A blocked run has no implied
permission to push or create a PR.

### `tasks.md`

`tasks.md` must record every ordered task's state, dependency, exact file
allowlist, iteration count, test commands and results, scope-check evidence, and
commit hash when committed. It must also record any human-approved allowlist
expansion, its reason, and the approval evidence. The task record must
distinguish completed, in-flight, and blocked work.

### `interfaces.md`

`interfaces.md` is the public-interface ledger derived from committed source. It
must record, per task and commit, exact function signatures, exported types,
routes/endpoints, configuration keys, and file paths created or changed. Record
`No public interface changes` when applicable, and append a superseding entry
instead of silently replacing historical entries.

## Blocked result

When status is `blocked`, codex-build must stop and return:

- the failed run-id and stopping task;
- completed tasks and partial commits;
- the uncommitted diff and exact changed paths;
- the failed command or iteration evidence and failure output;
- the diagnosis, attempted corrections, and why the loop stopped;
- the last green tests and currently failing or unrun gates;
- any worktree/state consistency concern that constrains the human's decision.

The blocked report references `run.md`, `tasks.md`, and `interfaces.md` rather
than replacing them. Fable returns it to the human and follows
`escalation.md`; it does not convert a blocked result into acceptance.

## Completed result

When status is `completed`, codex-build must return:

- all completed tasks and their commit hashes;
- final scope-check and full-suite evidence;
- final commit, branch, and a concise diff summary;
- human push-approval evidence and the PR URL;
- deviations, remaining work, deferred items, and explicit follow-ups;
- the paths to `run.md`, `tasks.md`, and `interfaces.md`.

“No remaining work” and “no follow-ups” must be stated explicitly when true.
Completion does not itself authorize merge.

## Fable acceptance-review input

Fable starts review only from a `completed` result. Required inputs are:

1. the Issue URL and full Issue body;
2. the human-approved plan and its approval evidence;
3. `run.md`, `tasks.md`, and `interfaces.md` from the same run-id;
4. the final repository diff and commits;
5. full-suite and per-task test evidence;
6. the PR URL and recorded deviations, remaining work, and follow-ups.

If an input is missing or inconsistent, Fable reports the affected criterion as
`BLOCKED` and asks the human for resolution; it does not invent evidence.

## Fable acceptance-review output

Fable writes a durable review record containing:

- Issue, plan, run-id, final commit, and PR references;
- one row per acceptance criterion with verdict `PASS`, `FAIL`, or `BLOCKED`;
- concrete evidence references for every verdict;
- guardrail, scope, test-gate, and interface-compatibility findings;
- deviations, remaining work, follow-ups, and material risks;
- an overall recommendation: `ACCEPT`, `REJECT`, or `NEEDS HUMAN DECISION`;
- decision log and reusable failure learnings.

Fable presents this record and its evidence to the human. Only the human makes
the merge decision; neither a `completed` run nor Fable's recommendation merges
the PR.
