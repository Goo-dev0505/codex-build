from __future__ import annotations

from pathlib import Path
import re
import unittest


REPO_ROOT = Path(__file__).resolve().parents[3]
COMMAND_PATH = REPO_ROOT / "commands" / "fable.md"
GUIDE_PATH = REPO_ROOT / "FABLE.md"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def normalize(value: str) -> str:
    return re.sub(r"\s+|\*\*", "", value)


def frontmatter(markdown: str) -> str:
    match = re.match(r"\A---\n(?P<body>.*?)\n---\n", markdown, re.DOTALL)
    if match is None:
        raise AssertionError("commands/fable.md must start with frontmatter")
    return match.group("body")


def frontmatter_tools(markdown: str) -> set[str]:
    body = frontmatter(markdown)
    match = re.search(
        r"(?ms)^allowed-tools:\s*\n(?P<items>(?:  - [^\n]+\n?)+)",
        body,
    )
    if match is None:
        raise AssertionError("frontmatter must define an allowed-tools list")
    return {
        item.strip()
        for item in re.findall(r"(?m)^  - ([^\n]+)$", match.group("items"))
    }


class CommandContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.command = read(COMMAND_PATH)
        cls.guide = read(GUIDE_PATH)

    def assert_contains_all(self, text: str, phrases: tuple[str, ...]) -> None:
        compact = normalize(text)
        for phrase in phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(normalize(phrase), compact)

    def test_frontmatter_defines_description_hint_and_required_tools(self) -> None:
        metadata = frontmatter(self.command)
        self.assertRegex(metadata, r"(?m)^description:\s*\S.+$")
        self.assertRegex(
            metadata,
            r"(?m)^argument-hint:\s*<issue-number-or-url>$",
        )
        self.assertTrue(
            {"Bash", "Read", "Write", "AskUserQuestion"}
            <= frontmatter_tools(self.command)
        )

    def test_command_requires_issue_when_argument_is_missing(self) -> None:
        self.assert_contains_all(
            self.command,
            (
                "`$1`",
                "`$ARGUMENTS`",
                "If `$1` is empty",
                "require an Issue number or Issue URL",
                "Do not guess, select, or infer an Issue",
            ),
        )

    def test_gh_is_optional_and_all_failures_use_complete_fallback(self) -> None:
        self.assert_contains_all(
            self.command,
            (
                "`command -v gh`",
                '`gh issue view "$1"`',
                "absent from `PATH`",
                "not authenticated",
                "`gh issue view` fails for any reason",
                "do not treat that failure as fatal",
                "do not require `gh` to be installed",
                "both the Issue URL and the complete Issue body",
                "then continue using those inputs",
            ),
        )

    def test_command_delegates_to_skill_and_validates_before_approval(self) -> None:
        self.assertGreaterEqual(
            self.command.count(
                "[`skills/fable/SKILL.md`](../skills/fable/SKILL.md)"
            ),
            2,
        )
        self.assert_contains_all(
            self.command,
            (
                "source of truth",
                "Do not duplicate or reimplement",
                "analyze the Issue",
                "`skills/fable/references/plan-template.md`",
                "`python3 skills/fable/scripts/validate_plan.py "
                "PLAN [--repo REPO]`",
                "complete validated plan",
                "explicit human approval",
                "before any execution handoff",
            ),
        )

    def test_command_does_not_duplicate_execution_loop(self) -> None:
        self.assertNotRegex(self.command, r"(?m)^### \d+\.")
        for loop_detail in (
            "one task per commit",
            "check_scope.py",
            "< /dev/null",
            "`run.md`",
            "`tasks.md`",
            "`interfaces.md`",
        ):
            with self.subTest(loop_detail=loop_detail):
                self.assertNotIn(loop_detail, self.command)


class InstallationGuideContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.guide = read(GUIDE_PATH)

    def assert_contains_all(self, text: str, phrases: tuple[str, ...]) -> None:
        compact = normalize(text)
        for phrase in phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(normalize(phrase), compact)

    def test_guide_installs_both_repo_sources_as_symlinks(self) -> None:
        self.assert_contains_all(
            self.guide,
            (
                "/Users/k.cross/Documents/10_Apps/fable-orchestrator",
                'COMMAND_LINK="$CLAUDE_CONFIG_DIR/commands/fable/run.md"',
                'SKILL_LINK="$CLAUDE_CONFIG_DIR/skills/fable"',
                'ln -s "$FABLE_REPO/commands/fable.md" "$COMMAND_LINK"',
                'ln -s "$FABLE_REPO/skills/fable" "$SKILL_LINK"',
                "`/fable:run <issue番号>`",
            ),
        )

    def test_install_preflight_refuses_files_directories_and_broken_links(self) -> None:
        self.assert_contains_all(
            self.guide,
            (
                'if [ -e "$destination" ] || [ -L "$destination" ]',
                "STOP: link destination already exists",
                "どちらかに該当した場合は上書きしない",
                "`ln -sf` は使わない",
            ),
        )
        self.assertNotIn("\nln -sf ", self.guide)
        self.assertNotRegex(self.guide, r"(?m)^\s*rm(?:\s|$)")
        self.assertNotRegex(self.guide, r"(?m)^\s*unlink(?:\s|$)")

    def test_guide_has_executable_verification_and_no_delete_update_policy(self) -> None:
        self.assert_contains_all(
            self.guide,
            (
                'test -L "$COMMAND_LINK"',
                'test -L "$SKILL_LINK"',
                'readlink "$COMMAND_LINK"',
                'readlink "$SKILL_LINK"',
                "/fable:run 123",
                "引数なしの `/fable:run`",
                "リンクを張り直す必要はない",
                "リンクまたは既存パスを削除・上書きして更新してはならない",
                "別名へ退避",
            ),
        )

    def test_upstream_maintenance_order_and_protected_integration(self) -> None:
        required_in_order = (
            "remote get-url upstream",
            "fetch upstream",
            "diff --name-status HEAD...upstream/main",
            "保護対象を守って統合する",
            "merge --no-ff upstream/main",
            "python3 -m unittest discover -s skills/fable/tests -v",
            "python3 -m unittest discover -s skills/codex-build/tests -v",
            "差分要約、テスト結果",
            "承認後に限り `git push`",
        )
        positions = []
        for phrase in required_in_order:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.guide)
            positions.append(self.guide.index(phrase))
        self.assertEqual(positions, sorted(positions))

        self.assert_contains_all(
            self.guide,
            (
                "upstream codex-build を直接改造しない",
                "`skills/codex-build/**`",
                "Fable 所有パスとの競合",
                "allowlist 外変更",
                "競合を推測で解消せず停止",
                "force-push は行わない",
            ),
        )

    def test_plugin_manifests_are_unneeded_and_forbidden(self) -> None:
        self.assert_contains_all(
            self.guide,
            (
                "plugin manifest の変更は導入にも更新にも不要",
                "`.claude-plugin/**`",
                "`.codex-plugin/**`",
                "変更は禁止",
                "manifest を Fable 用に拡張する対応は禁止",
            ),
        )


if __name__ == "__main__":
    unittest.main()
