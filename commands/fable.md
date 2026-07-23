---
description: Analyze a GitHub Issue, validate an implementation plan, obtain human approval, and hand execution to Fable
argument-hint: <issue-number-or-url>
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - AskUserQuestion
---

Start Fable for the Issue selected by `$1`.

Full argument string: `$ARGUMENTS`

[`skills/fable/SKILL.md`](../skills/fable/SKILL.md) is the source of truth for
the complete Fable workflow, its eleven steps, phase boundaries, and execution
handoff. Read and follow that skill. Do not duplicate or reimplement its
workflow or the codex-build execution loop in this command.

## Issue input

- If `$1` is empty, use `AskUserQuestion` to require an Issue number or Issue
  URL. Do not guess, select, or infer an Issue.
- If `command -v gh` succeeds, attempt to obtain the requested Issue with
  `gh issue view "$1"`. Capture at least its URL, title, and full body.
- If `gh` is absent from `PATH`, is not authenticated, or `gh issue view`
  fails for any reason, do not treat that failure as fatal and do not require
  `gh` to be installed. Use `AskUserQuestion` to require **both** the Issue URL
  and the complete Issue body from the human. Wait until both are supplied,
  then continue using those inputs.

## Canonical handoff

After the Issue input is complete, delegate to
[`skills/fable/SKILL.md`](../skills/fable/SKILL.md). Under that canonical
workflow, analyze the Issue, create the plan from
[`skills/fable/references/plan-template.md`](../skills/fable/references/plan-template.md),
and validate it with:

`python3 skills/fable/scripts/validate_plan.py PLAN [--repo REPO]`

Present the complete validated plan and obtain explicit human approval before
any execution handoff. After approval, continue only through the delegation and
phase-boundary rules in `skills/fable/SKILL.md`; the command itself owns no
execution-loop behavior.
