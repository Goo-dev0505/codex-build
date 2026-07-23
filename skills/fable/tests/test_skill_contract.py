from __future__ import annotations

from pathlib import Path
import re
import unittest


SKILL_DIR = Path(__file__).parents[1]
SKILL = SKILL_DIR / "SKILL.md"
ESCALATION = SKILL_DIR / "references" / "escalation.md"
RESULT_CONTRACT = SKILL_DIR / "references" / "result-contract.md"

PUSH_RULE = (
    "push・PR作成は、diff要約を提示して人間の明示"
    "承認を得た後にのみ行う。承認前は必ず停止する。"
)

STEP_REQUIREMENTS = {
    1: ("human", "Issue", "starts Fable"),
    2: (
        "`gh issue view`",
        "Issue URL",
        "full Issue body",
        "requirements",
        "completion conditions",
        "affected scope",
        "risks",
    ),
    3: (
        "high-risk",
        "authentication",
        "billing",
        "data deletion",
        "secrets",
        "external publication",
        "sub-Issue",
        "human's approval",
    ),
    4: (
        "`references/plan-template.md`",
        "`plan-example.md`",
        "acceptance criteria",
        "file allowlists",
        "test commands",
        PUSH_RULE,
    ),
    5: (
        "`python3 skills/fable/scripts/validate_plan.py PLAN [--repo REPO]`",
        "exit status 0",
        "1",
        "2",
        "invalid plan",
    ),
    6: (
        "explicit approval",
        "`APPROVED`",
        "approver",
        "approval evidence",
        "approval date",
        "validate it again",
    ),
    7: (
        "codex-build",
        "transfer control",
        "Fable does not intervene",
        "completed or blocked",
    ),
    8: (
        "all ordered tasks",
        "full-suite gate",
        "before push",
        "diff summary",
        "explicit approval",
        PUSH_RULE,
        "single PR",
    ),
    9: (
        "STOP",
        "return control to the human",
        "later turn",
        "explicit instruction",
        "Never replan automatically",
        "`references/escalation.md`",
    ),
    10: (
        "acceptance criterion",
        "verdict",
        "evidence",
        "human alone",
        "merge",
    ),
    11: (
        "decisions",
        "deviations",
        "follow-ups",
        "failure learnings",
        "source of truth",
    ),
}


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def numbered_sections(markdown: str, heading_level: int) -> list[tuple[int, str]]:
    marker = "#" * heading_level
    pattern = re.compile(
        rf"^{marker} (?P<number>\d+)\. [^\n]+$"
        rf"(?P<body>.*?)(?=^{marker} \d+\. |\Z)",
        re.MULTILINE | re.DOTALL,
    )
    return [
        (int(match.group("number")), match.group("body").strip())
        for match in pattern.finditer(markdown)
    ]


def section(markdown: str, heading: str) -> str:
    pattern = re.compile(
        rf"^## {re.escape(heading)}\s*$"
        r"(?P<body>.*?)(?=^## |\Z)",
        re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(markdown)
    if match is None:
        raise AssertionError(f"missing section: {heading}")
    return match.group("body").strip()


def normalized(value: str) -> str:
    return " ".join(value.split())


class SkillContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.skill = read(SKILL)
        cls.escalation = read(ESCALATION)
        cls.result = read(RESULT_CONTRACT)

    def assert_contains_all(self, text: str, phrases: tuple[str, ...]) -> None:
        compact_text = normalized(text)
        for phrase in phrases:
            self.assertIn(normalized(phrase), compact_text)

    def test_skill_has_valid_frontmatter(self) -> None:
        match = re.match(r"\A---\n(?P<body>.*?)\n---\n", self.skill, re.DOTALL)
        self.assertIsNotNone(match, "SKILL.md must start with YAML frontmatter")
        frontmatter = match.group("body") if match else ""
        self.assertRegex(frontmatter, r"(?m)^name: fable$")
        description = re.search(r'(?m)^description:\s*"([^"]+)"$', frontmatter)
        self.assertIsNotNone(description)
        self.assertGreater(len(description.group(1).strip()), 30)

    def test_eleven_steps_have_fixed_numbers_order_and_substance(self) -> None:
        steps = numbered_sections(self.skill, 3)
        self.assertEqual([number for number, _ in steps], list(range(1, 12)))

        for number, body in steps:
            with self.subTest(step=number):
                self.assertGreaterEqual(
                    len(body.split()),
                    12,
                    f"step {number} is not a substantive contract",
                )
                self.assert_contains_all(body, STEP_REQUIREMENTS[number])

    def test_phase_boundary_separates_planning_build_and_acceptance(self) -> None:
        boundary = section(
            self.skill,
            "Phase boundary and non-negotiable invariants",
        )
        planning = boundary.index("Fable planning phase (steps 1–6)")
        build = boundary.index("codex-build execution phase (steps 7–9)")
        acceptance = boundary.index("Fable acceptance phase (steps 10–11)")
        self.assertLess(planning, build)
        self.assertLess(build, acceptance)
        self.assert_contains_all(
            boundary,
            (
                "non-overlapping phases",
                "Fable is inactive and does not intervene",
                "Do not blend Fable planning or acceptance work into the "
                "execution phase",
            ),
        )

    def test_codex_exec_and_fable_non_authoring_are_invariants(self) -> None:
        boundary = section(
            self.skill,
            "Phase boundary and non-negotiable invariants",
        )
        self.assert_contains_all(
            boundary,
            (
                "Product code and every task deliverable must be created "
                "through `codex exec`.",
                "Fable itself never writes product code or task deliverables.",
            ),
        )
        step_seven = dict(numbered_sections(self.skill, 3))[7]
        self.assert_contains_all(
            step_seven,
            (
                "does not intervene",
                "edit deliverables",
                "commit",
                "push",
                "create a PR",
            ),
        )

    def test_push_gate_is_exact_and_applies_before_push_and_pr(self) -> None:
        steps = dict(numbered_sections(self.skill, 3))
        self.assertIn(PUSH_RULE, steps[4])
        self.assertIn(PUSH_RULE, steps[8])
        self.assertIn("all ordered tasks", steps[8])
        self.assertIn("full-suite gate must be green", steps[8])
        self.assertLess(steps[8].index("stop"), steps[8].index("push and create"))
        self.assertNotIn("Ask before pushing", self.skill)

    def test_stop_escalation_has_fixed_order_and_no_same_turn_restart(self) -> None:
        stages = numbered_sections(self.escalation, 2)
        self.assertEqual([number for number, _ in stages], [1, 2, 3, 4])
        headings = re.findall(r"^## \d+\. (.+)$", self.escalation, re.MULTILINE)
        self.assertEqual(
            headings,
            ["STOP", "人間へ返す", "人間の後続ターンでの明示指示", "再計画"],
        )
        self.assertIn(
            "`STOP → 人間へ返す → 人間の後続ターンでの明示指示 → 再計画`",
            self.escalation,
        )
        self.assert_contains_all(
            stages[0][1],
            (
                "must not trigger automatic replanning",
                "must not restart the run in the same turn",
            ),
        )
        self.assert_contains_all(
            stages[2][1],
            ("explicit replanning instruction in a later turn",),
        )

    def test_replanning_preserves_failed_run_and_retires_current_by_rename(self) -> None:
        replan = dict(numbered_sections(self.escalation, 2))[4]
        self.assert_contains_all(
            replan,
            (
                "failed run's `run.md`, `tasks.md`, `interfaces.md`",
                "completed and partial commit",
                "exact new base",
                "how each partial commit is handled",
                "`$GIT_DIR/codex-build/runs/<run-id>/`",
                "no run directory or file within it may be deleted",
                "`$GIT_DIR/codex-build/current`",
                "Atomically rename",
                "`current.archived.<UTC-timestamp>.<old-run-id>`",
                "archive/rename operation, not removal or overwrite",
                "fresh, never-reused run-id",
                "`runs/<new-run-id>/`",
            ),
        )
        self.assertLess(replan.index("Atomically rename"), replan.index("fresh"))
        for destructive_command in ("rm -", "unlink(", "rmtree(", "git reset"):
            self.assertNotIn(destructive_command, self.escalation)

    def test_result_files_define_substantive_canonical_evidence(self) -> None:
        sources = section(self.result, "Sources of truth")
        self.assertIn(
            "`$GIT_DIR/codex-build/runs/<run-id>/`",
            sources,
        )
        self.assertIn("Execution state is canonical", sources)
        self.assertIn("approved plan is the source of truth", sources)
        self.assertIn("Fable-side plan and acceptance-review record", sources)

        required = section(self.result, "Required execution files")
        for filename in ("`run.md`", "`tasks.md`", "`interfaces.md`"):
            self.assertIn(f"### {filename}", required)
        self.assert_contains_all(
            required,
            (
                "`completed` or `blocked`",
                "full-suite evidence",
                "push-approval",
                "exact file allowlist",
                "iteration count",
                "test commands and results",
                "scope-check evidence",
                "commit hash",
                "public-interface ledger",
                "exact function signatures",
                "routes/endpoints",
                "configuration keys",
            ),
        )

    def test_blocked_and_completed_results_cover_diagnostics_and_followups(self) -> None:
        blocked = section(self.result, "Blocked result")
        self.assert_contains_all(
            blocked,
            (
                "stopping task",
                "partial commits",
                "uncommitted diff",
                "exact changed paths",
                "failure output",
                "diagnosis",
                "attempted corrections",
                "currently failing or unrun gates",
            ),
        )

        completed = section(self.result, "Completed result")
        self.assert_contains_all(
            completed,
            (
                "commit hashes",
                "scope-check",
                "full-suite evidence",
                "diff summary",
                "push-approval evidence",
                "PR URL",
                "remaining work",
                "deferred items",
                "follow-ups",
            ),
        )

    def test_acceptance_review_has_required_inputs_outputs_and_human_merge(self) -> None:
        inputs = section(self.result, "Fable acceptance-review input")
        self.assert_contains_all(
            inputs,
            (
                "Issue URL and full Issue body",
                "human-approved plan",
                "`run.md`, `tasks.md`, and `interfaces.md`",
                "final repository diff and commits",
                "test evidence",
                "PR URL",
                "remaining work",
                "follow-ups",
                "reports the affected criterion as `BLOCKED`",
            ),
        )

        outputs = section(self.result, "Fable acceptance-review output")
        self.assert_contains_all(
            outputs,
            (
                "one row per acceptance criterion",
                "`PASS`, `FAIL`, or `BLOCKED`",
                "evidence references",
                "guardrail",
                "scope",
                "test-gate",
                "interface-compatibility",
                "`ACCEPT`, `REJECT`, or `NEEDS HUMAN DECISION`",
                "decision log",
                "failure learnings",
                "Only the human makes the merge decision",
            ),
        )


if __name__ == "__main__":
    unittest.main()
