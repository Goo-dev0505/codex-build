from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).parents[1] / "scripts" / "validate_plan.py"
TEMPLATE = Path(__file__).parents[1] / "references" / "plan-template.md"
SPEC = importlib.util.spec_from_file_location("validate_plan", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot import validator from {SCRIPT}")
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)
validate_plan = VALIDATOR.validate_plan

PUSH_RULE = (
    "push・PR作成は、diff要約を提示して人間の明示"
    "承認を得た後にのみ行う。承認前は必ず停止する。"
)

VALID_PLAN = f"""\
# Plan: add a validator

## Approval

- **Status:** `APPROVED`
- **Approver:** KITAcore
- **Approval evidence:** user message "approved for implementation"
- **Approval date:** 2026-07-23

## Issue / Source

- **Issue:** https://github.com/example/project/issues/42
- **Source:** issue body and design review
- **Repository:** example/project

## Context

Plans need deterministic validation before execution.

## Acceptance criteria

- The validator accepts this complete plan.
- Invalid task file declarations produce actionable diagnostics.

## Branch & PR

- **Branch:** `feat/plan-validator`
- **PR target:** `main`
- **PR unit:** `1 Issue = 1 plan = 1 PR`

## Model / Effort

- **Model:** `gpt-5.6-sol`
- **Effort:** `high`
- **Pinning:** fixed at run start

## Risk

- **Level:** `low`
- **Rationale:** local Markdown and standard-library Python only

## Guardrails (things this plan bans)

- Only task Files may change.
- {PUSH_RULE}

## Test commands (the gate)

- `python3 -m unittest discover -s skills/fable/tests -v`

## Tasks (ordered)

### T1 — validator core

- **Goal:** validate the plan contract
- **Files:** `skills/fable/scripts/validate_plan.py`,
  `skills/fable/tests/test_validate_plan.py`
- **Constraints:** use the Python standard library only
- **Dependencies:** None
- **Tests:** `python3 -m unittest skills.fable.tests.test_validate_plan -v`
- **Completion criteria:** positive and negative cases pass

### T2 — usage documentation

- **Goal:** document validator invocation
- **Files:** `docs/plan-validation.md`
- **Constraints:** do not change the validator interface
- **Dependencies:** T1
- **Tests:** `python3 -m unittest discover -s skills/fable/tests -v`
- **Completion criteria:** the full test gate passes
"""


class ValidatePlanTests(unittest.TestCase):
    def assert_has_error(self, markdown: str, expected: str) -> None:
        """Assert that validation fails with a useful matching diagnostic."""
        errors = validate_plan(markdown)
        self.assertTrue(errors, "invalid plan unexpectedly passed")
        self.assertTrue(
            any(expected in error for error in errors),
            f"expected diagnostic containing {expected!r}, got: {errors}",
        )

    def test_accepts_complete_approved_plan(self) -> None:
        self.assertEqual(validate_plan(VALID_PLAN), [])

    def test_template_carries_sources_task_schema_and_exact_push_rule(self) -> None:
        template = TEMPLATE.read_text(encoding="utf-8")

        self.assertIn("docs/20260723_fable-mvp-plan.md", template)
        self.assertIn("docs/20260723_fable-design-review.md", template)
        self.assertIn(PUSH_RULE, template)
        self.assertIn("- **Status:** `PENDING`", template)
        for field in VALIDATOR.REQUIRED_TASK_FIELDS:
            self.assertIn(f"- **{field}:**", template)

    def test_unindented_prose_does_not_extend_metadata_field(self) -> None:
        plan = VALID_PLAN.replace(
            "- **Approval date:** 2026-07-23",
            "- **Approval date:** 2026-07-23\n\n"
            "This prose explains how the approval was recorded.",
        )

        self.assertEqual(validate_plan(plan), [])

    def test_rejects_missing_required_section(self) -> None:
        invalid = VALID_PLAN.replace(
            "## Acceptance criteria\n\n"
            "- The validator accepts this complete plan.\n"
            "- Invalid task file declarations produce actionable diagnostics.\n\n",
            "",
        )

        self.assert_has_error(
            invalid,
            "missing required section '## Acceptance criteria'",
        )

    def test_rejects_plan_without_human_approval(self) -> None:
        invalid = VALID_PLAN.replace("`APPROVED`", "`PENDING`", 1)

        self.assert_has_error(invalid, "Status must be exactly 'APPROVED'")
        self.assert_has_error(invalid, "field 'Status' must have a concrete value")

    def test_rejects_missing_approval_evidence(self) -> None:
        invalid = VALID_PLAN.replace(
            '- **Approval evidence:** user message "approved for implementation"',
            "- **Approval evidence:**",
        )

        self.assert_has_error(
            invalid,
            "field 'Approval evidence' must have a concrete value",
        )

    def test_rejects_wrong_approval_date_format(self) -> None:
        invalid = VALID_PLAN.replace("2026-07-23", "July 23, 2026", 1)

        self.assert_has_error(invalid, "valid date in YYYY-MM-DD format")

    def test_rejects_nonexistent_approval_date(self) -> None:
        invalid = VALID_PLAN.replace("2026-07-23", "2026-02-31", 1)

        self.assert_has_error(invalid, "valid date in YYYY-MM-DD format")

    def test_rejects_missing_exact_push_rule(self) -> None:
        invalid = VALID_PLAN.replace(PUSH_RULE, "Ask before pushing.")

        self.assert_has_error(invalid, "exact push/PR approval rule")

    def test_rejects_non_consecutive_task_numbers(self) -> None:
        invalid = VALID_PLAN.replace(
            "### T2 — usage documentation",
            "### T3 — usage documentation",
        )

        self.assert_has_error(invalid, "task numbers must be consecutive from T1")

    def test_rejects_malformed_task_heading(self) -> None:
        invalid = VALID_PLAN.replace("### T2 — usage documentation", "### task two")

        self.assert_has_error(invalid, "malformed task heading")

    def test_rejects_each_missing_task_field(self) -> None:
        for field in VALIDATOR.REQUIRED_TASK_FIELDS:
            with self.subTest(field=field):
                line = next(
                    line
                    for line in VALID_PLAN.splitlines()
                    if line.startswith(f"- **{field}:**")
                )
                invalid = VALID_PLAN.replace(f"{line}\n", "", 1)
                self.assert_has_error(invalid, f"missing required field '{field}'")

    def test_rejects_absolute_file_path(self) -> None:
        invalid = VALID_PLAN.replace(
            "`docs/plan-validation.md`",
            "`/tmp/plan-validation.md`",
        )

        self.assert_has_error(invalid, "must be repo-relative, not absolute")

    def test_rejects_windows_absolute_file_path(self) -> None:
        invalid = VALID_PLAN.replace(
            "`docs/plan-validation.md`",
            "`C:\\temp\\plan-validation.md`",
        )

        self.assert_has_error(invalid, "absolute Windows path")

    def test_rejects_directory_file_entry(self) -> None:
        invalid = VALID_PLAN.replace(
            "`docs/plan-validation.md`",
            "`docs/`",
        )

        self.assert_has_error(invalid, "names a directory, not a file")

    def test_rejects_existing_directory_without_trailing_slash(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            (repo / "docs").mkdir()
            invalid = VALID_PLAN.replace(
                "`docs/plan-validation.md`",
                "`docs`",
            )

            errors = validate_plan(invalid, repo_root=repo)

        self.assertTrue(
            any("names an existing directory" in error for error in errors),
            errors,
        )

    def test_rejects_glob_file_entry(self) -> None:
        invalid = VALID_PLAN.replace(
            "`docs/plan-validation.md`",
            "`docs/*.md`",
        )

        self.assert_has_error(invalid, "glob syntax is not allowed")

    def test_rejects_dot_and_dot_dot_path_segments(self) -> None:
        for path in ("docs/./plan.md", "docs/../plan.md"):
            with self.subTest(path=path):
                invalid = VALID_PLAN.replace(
                    "`docs/plan-validation.md`",
                    f"`{path}`",
                )
                self.assert_has_error(invalid, "'.' or '..' path segments")

    def test_rejects_plain_text_in_files_allowlist(self) -> None:
        invalid = VALID_PLAN.replace(
            "`docs/plan-validation.md`",
            "`docs/plan-validation.md` and related files",
        )

        self.assert_has_error(invalid, "only comma-separated backticked paths")

    def test_rejects_missing_global_test_command(self) -> None:
        invalid = VALID_PLAN.replace(
            "- `python3 -m unittest discover -s skills/fable/tests -v`\n\n"
            "## Tasks (ordered)",
            "- run the relevant suite\n\n## Tasks (ordered)",
        )

        self.assert_has_error(
            invalid,
            "must contain at least one backticked executable",
        )

    def test_rejects_non_command_task_tests(self) -> None:
        invalid = VALID_PLAN.replace(
            "`python3 -m unittest skills.fable.tests.test_validate_plan -v`",
            "manual review",
            1,
        )

        self.assert_has_error(invalid, "Tests must contain a backticked executable")

    def test_rejects_dependency_on_later_task(self) -> None:
        invalid = VALID_PLAN.replace(
            "- **Dependencies:** None",
            "- **Dependencies:** T2",
            1,
        )

        self.assert_has_error(invalid, "may reference only earlier tasks")

    def test_rejects_unknown_dependency(self) -> None:
        invalid = VALID_PLAN.replace(
            "- **Dependencies:** T1",
            "- **Dependencies:** T9",
            1,
        )

        self.assert_has_error(invalid, "references unknown T9")

    def test_cli_returns_zero_for_valid_plan(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            plan_path = Path(temp_dir) / "plan.md"
            plan_path.write_text(VALID_PLAN, encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(SCRIPT), str(plan_path), "--repo", temp_dir],
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("plan validation passed", result.stdout)

    def test_cli_returns_nonzero_with_specific_diagnostics(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            plan_path = Path(temp_dir) / "plan.md"
            plan_path.write_text(
                VALID_PLAN.replace("`docs/plan-validation.md`", "`docs/*.md`"),
                encoding="utf-8",
            )
            result = subprocess.run(
                [sys.executable, str(SCRIPT), str(plan_path), "--repo", temp_dir],
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(result.returncode, 1)
        self.assertIn("docs/*.md", result.stderr)
        self.assertIn("glob syntax is not allowed", result.stderr)


if __name__ == "__main__":
    unittest.main()
