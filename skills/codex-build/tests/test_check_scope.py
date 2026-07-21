from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).parents[1] / "scripts" / "check_scope.py"


class CheckScopeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp_dir.name)
        self.git("init", "-q")
        self.git("config", "user.email", "codex-build@example.test")
        self.git("config", "user.name", "Codex Build Tests")
        self.write("allowed.txt", "original\n")
        self.write("outside.txt", "original\n")
        self.write(".gitignore", "ignored/\n")
        self.git("add", ".")
        self.git("commit", "-qm", "initial")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def git(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", "-C", str(self.repo), *args],
            check=True,
            capture_output=True,
            text=True,
        )

    def write(self, relative_path: str, content: str) -> None:
        path = self.repo / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def check(self, *allowed_paths: str) -> subprocess.CompletedProcess[str]:
        allowlist = self.repo.parent / f"allowlist-{self._testMethodName}.txt"
        allowlist.write_text("\n".join(allowed_paths) + "\n", encoding="utf-8")
        self.addCleanup(allowlist.unlink, missing_ok=True)
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--repo",
                str(self.repo),
                "--allowlist",
                str(allowlist),
            ],
            check=False,
            capture_output=True,
            text=True,
        )

    def test_allows_declared_tracked_change(self) -> None:
        self.write("allowed.txt", "changed\n")

        result = self.check("allowed.txt")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("1 changed path", result.stdout)

    def test_rejects_tracked_change_outside_allowlist(self) -> None:
        self.write("outside.txt", "changed\n")

        result = self.check("allowed.txt")

        self.assertEqual(result.returncode, 1)
        self.assertIn("outside.txt", result.stderr)

    def test_rejects_untracked_file_outside_allowlist(self) -> None:
        self.write("new file.txt", "new\n")

        result = self.check("allowed.txt")

        self.assertEqual(result.returncode, 1)
        self.assertIn("new file.txt", result.stderr)

    def test_ignores_gitignored_build_output(self) -> None:
        self.write("ignored/build.log", "generated\n")

        result = self.check("allowed.txt")

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_rejects_deleted_file_outside_allowlist(self) -> None:
        (self.repo / "outside.txt").unlink()

        result = self.check("allowed.txt")

        self.assertEqual(result.returncode, 1)
        self.assertIn("outside.txt", result.stderr)

    def test_staged_rename_requires_both_paths(self) -> None:
        self.git("mv", "outside.txt", "renamed.txt")

        rejected = self.check("renamed.txt")
        accepted = self.check("outside.txt", "renamed.txt")

        self.assertEqual(rejected.returncode, 1)
        self.assertIn("outside.txt", rejected.stderr)
        self.assertEqual(accepted.returncode, 0, accepted.stderr)

    def test_rejects_non_normalized_allowlist_path(self) -> None:
        result = self.check("../allowed.txt")

        self.assertEqual(result.returncode, 2)
        self.assertIn("not an exact repo-relative file", result.stderr)


if __name__ == "__main__":
    unittest.main()
