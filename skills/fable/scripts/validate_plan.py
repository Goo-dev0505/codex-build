#!/usr/bin/env python3
"""Validate an approved Fable implementation plan written in Markdown."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from datetime import date
from pathlib import Path, PurePosixPath
import re
import shlex
import sys


PUSH_APPROVAL_RULE = (
    "push・PR作成は、diff要約を提示して人間の明示"
    "承認を得た後にのみ行う。承認前は必ず停止する。"
)

REQUIRED_SECTIONS = (
    "Approval",
    "Issue / Source",
    "Context",
    "Acceptance criteria",
    "Branch & PR",
    "Model / Effort",
    "Risk",
    "Guardrails (things this plan bans)",
    "Test commands (the gate)",
    "Tasks (ordered)",
)

REQUIRED_TASK_FIELDS = (
    "Goal",
    "Files",
    "Constraints",
    "Dependencies",
    "Tests",
    "Completion criteria",
)

_SECTION_HEADING_RE = re.compile(r"^##[ \t]+(.+?)[ \t]*#*[ \t]*$", re.MULTILINE)
_TASK_HEADING_RE = re.compile(r"^###[ \t]+(.+?)[ \t]*#*[ \t]*$", re.MULTILINE)
_TASK_TITLE_RE = re.compile(
    r"^T(?P<number>[1-9]\d*)[ \t]+(?:—|-)[ \t]+(?P<title>\S.*)$"
)
_FIELD_RE = re.compile(r"^-\s+\*\*(?P<label>[^*]+):\*\*\s*(?P<value>.*)$")
_CODE_SPAN_RE = re.compile(r"(?<!`)`([^`\n]+)`(?!`)")
_PLACEHOLDER_RE = re.compile(
    r"<[^>\n]+>|\b(?:TBD|TODO|FIXME|PENDING|UNKNOWN)\b",
    re.IGNORECASE,
)
_URL_RE = re.compile(r"https://[^\s<>)]+")
_WINDOWS_ABSOLUTE_RE = re.compile(r"^[A-Za-z]:[\\/]")
_GLOB_CHARACTERS = frozenset("*?[]{}")


def _split_sections(markdown: str) -> tuple[dict[str, str], list[str]]:
    """Return level-two section bodies and duplicate-section diagnostics."""
    matches = list(_SECTION_HEADING_RE.finditer(markdown))
    sections: dict[str, str] = {}
    errors: list[str] = []

    for index, match in enumerate(matches):
        name = match.group(1).strip()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(markdown)
        if name in sections:
            errors.append(f"section {name!r} appears more than once")
            continue
        sections[name] = markdown[match.end() : end].strip()

    return sections, errors


def _parse_labeled_fields(body: str) -> dict[str, str]:
    """Parse bold Markdown list labels and their continuation lines."""
    fields: dict[str, list[str]] = {}
    current_label: str | None = None

    for line in body.splitlines():
        match = _FIELD_RE.match(line)
        if match:
            current_label = match.group("label").strip()
            fields.setdefault(current_label, []).append(match.group("value").strip())
        elif current_label is not None and line.startswith((" ", "\t")):
            fields[current_label].append(line.strip())
        elif line:
            current_label = None

    return {
        label: "\n".join(parts).strip()
        for label, parts in fields.items()
    }


def _plain_markdown(value: str) -> str:
    """Remove simple inline Markdown used around metadata values."""
    return value.strip().strip("`").strip().strip("*").strip()


def _is_meaningful(value: str) -> bool:
    """Return whether a value is non-empty and contains no template marker."""
    plain = _plain_markdown(value)
    return bool(plain) and _PLACEHOLDER_RE.search(plain) is None


def _require_fields(
    section_name: str,
    fields: dict[str, str],
    required: Sequence[str],
) -> list[str]:
    """Return diagnostics for missing or placeholder-valued fields."""
    errors: list[str] = []
    for label in required:
        if label not in fields:
            errors.append(f"{section_name}: missing required field {label!r}")
        elif not _is_meaningful(fields[label]):
            errors.append(f"{section_name}: field {label!r} must have a concrete value")
    return errors


def _command_strings(value: str) -> list[str]:
    """Extract executable-looking inline-code command strings."""
    commands: list[str] = []
    for raw_command in _CODE_SPAN_RE.findall(value):
        command = raw_command.strip()
        if not command or "\n" in command or _PLACEHOLDER_RE.search(command):
            continue
        try:
            tokens = shlex.split(command)
        except ValueError:
            continue
        while tokens and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", tokens[0]):
            tokens.pop(0)
        if not tokens:
            continue
        executable = tokens[0]
        if executable in {"|", "||", "&&", ";"} or executable.startswith("-"):
            continue
        if re.fullmatch(r"[A-Za-z0-9_./+-]+", executable):
            commands.append(command)
    return commands


def _validate_file_path(raw_path: str, repo_root: Path | None) -> str | None:
    """Return a diagnostic when a task Files entry is not an exact file path."""
    if raw_path != raw_path.strip():
        return "has leading or trailing whitespace"
    if not raw_path:
        return "is empty"
    if _WINDOWS_ABSOLUTE_RE.match(raw_path):
        return "must be repo-relative, not an absolute Windows path"
    if "\\" in raw_path:
        return "must use Git-style '/' separators"
    if any(character in raw_path for character in _GLOB_CHARACTERS):
        return "must name one exact file; glob syntax is not allowed"

    candidate = PurePosixPath(raw_path)
    parts = raw_path.split("/")
    if candidate.is_absolute() or raw_path.startswith("~"):
        return "must be repo-relative, not absolute"
    if raw_path.endswith("/"):
        return "names a directory, not a file"
    if any(part in {"", ".", ".."} for part in parts):
        return "must not contain empty, '.' or '..' path segments"

    if repo_root is not None:
        resolved_candidate = repo_root.joinpath(*parts)
        if resolved_candidate.is_dir():
            return "names an existing directory, not a file"

    return None


def _validate_files(
    task_name: str,
    value: str,
    repo_root: Path | None,
) -> list[str]:
    """Validate a task's exact repo-relative file allowlist."""
    errors: list[str] = []
    paths = [path.strip() for path in _CODE_SPAN_RE.findall(value)]
    remainder = _CODE_SPAN_RE.sub("", value)

    if not paths:
        return [f"{task_name}: Files must contain at least one backticked file path"]
    if re.sub(r"[\s,、]+", "", remainder):
        errors.append(
            f"{task_name}: Files may contain only comma-separated backticked paths"
        )

    seen: set[str] = set()
    for raw_path in paths:
        if raw_path in seen:
            errors.append(f"{task_name}: Files contains duplicate path {raw_path!r}")
            continue
        seen.add(raw_path)
        problem = _validate_file_path(raw_path, repo_root)
        if problem is not None:
            errors.append(f"{task_name}: invalid Files path {raw_path!r}: {problem}")

    return errors


def _validate_metadata(sections: dict[str, str]) -> list[str]:
    """Validate approval and plan-level metadata sections."""
    errors: list[str] = []

    approval = _parse_labeled_fields(sections["Approval"])
    errors.extend(
        _require_fields(
            "Approval",
            approval,
            ("Status", "Approver", "Approval evidence", "Approval date"),
        )
    )
    status = _plain_markdown(approval.get("Status", ""))
    if status != "APPROVED":
        errors.append("Approval: Status must be exactly 'APPROVED'")
    approval_date = _plain_markdown(approval.get("Approval date", ""))
    if approval_date:
        try:
            date.fromisoformat(approval_date)
        except ValueError:
            errors.append(
                "Approval: Approval date must be a valid date in YYYY-MM-DD format"
            )

    issue = _parse_labeled_fields(sections["Issue / Source"])
    errors.extend(
        _require_fields(
            "Issue / Source",
            issue,
            ("Issue", "Source", "Repository"),
        )
    )
    if "Issue" in issue and _URL_RE.search(issue["Issue"]) is None:
        errors.append("Issue / Source: Issue must contain an https URL")

    branch = _parse_labeled_fields(sections["Branch & PR"])
    errors.extend(
        _require_fields(
            "Branch & PR",
            branch,
            ("Branch", "PR target", "PR unit"),
        )
    )

    model = _parse_labeled_fields(sections["Model / Effort"])
    errors.extend(
        _require_fields(
            "Model / Effort",
            model,
            ("Model", "Effort", "Pinning"),
        )
    )

    risk = _parse_labeled_fields(sections["Risk"])
    errors.extend(_require_fields("Risk", risk, ("Level", "Rationale")))
    level = _plain_markdown(risk.get("Level", "")).lower()
    if level and level not in {"low", "medium", "high"}:
        errors.append("Risk: Level must be one of low, medium or high")

    if not _is_meaningful(sections["Context"]):
        errors.append("Context must contain a concrete description")

    criteria = [
        line[2:].strip()
        for line in sections["Acceptance criteria"].splitlines()
        if line.startswith("- ")
    ]
    if not any(_is_meaningful(item) for item in criteria):
        errors.append(
            "Acceptance criteria must contain at least one concrete list item"
        )

    guardrails = sections["Guardrails (things this plan bans)"]
    if PUSH_APPROVAL_RULE not in guardrails:
        errors.append(
            "Guardrails must contain the exact push/PR approval rule: "
            f"{PUSH_APPROVAL_RULE}"
        )

    if not _command_strings(sections["Test commands (the gate)"]):
        errors.append(
            "Test commands (the gate) must contain at least one backticked "
            "executable command string"
        )

    return errors


def _validate_tasks(
    tasks_body: str,
    repo_root: Path | None,
) -> list[str]:
    """Validate ordered tasks and every task-level contract field."""
    errors: list[str] = []
    matches = list(_TASK_HEADING_RE.finditer(tasks_body))
    if not matches:
        return ["Tasks (ordered) must contain at least one '### T1 — ...' task"]

    parsed_tasks: list[tuple[int, str, str]] = []
    for index, match in enumerate(matches):
        heading = match.group(1).strip()
        title_match = _TASK_TITLE_RE.fullmatch(heading)
        if title_match is None:
            errors.append(
                f"Tasks (ordered): malformed task heading {heading!r}; "
                "expected 'T<number> — <title>'"
            )
            continue
        end = (
            matches[index + 1].start()
            if index + 1 < len(matches)
            else len(tasks_body)
        )
        parsed_tasks.append(
            (
                int(title_match.group("number")),
                heading,
                tasks_body[match.end() : end].strip(),
            )
        )

    numbers = [number for number, _, _ in parsed_tasks]
    expected = list(range(1, len(parsed_tasks) + 1))
    if numbers != expected:
        errors.append(
            "Tasks (ordered): task numbers must be consecutive from T1; "
            f"found {', '.join(f'T{number}' for number in numbers) or 'none'}"
        )

    available_numbers = set(numbers)
    for number, heading, body in parsed_tasks:
        task_name = f"T{number}"
        fields = _parse_labeled_fields(body)
        errors.extend(_require_fields(task_name, fields, REQUIRED_TASK_FIELDS))

        if "Files" in fields:
            errors.extend(_validate_files(task_name, fields["Files"], repo_root))

        tests = fields.get("Tests", "")
        if tests and not _command_strings(tests):
            errors.append(
                f"{task_name}: Tests must contain a backticked executable "
                "command string"
            )

        dependencies = _plain_markdown(fields.get("Dependencies", ""))
        if dependencies and dependencies.lower() not in {"none", "なし"}:
            referenced = {
                int(value)
                for value in re.findall(r"\bT([1-9]\d*)\b", dependencies)
            }
            if not referenced:
                errors.append(
                    f"{task_name}: Dependencies must be None or reference T numbers"
                )
            for dependency in sorted(referenced):
                if dependency not in available_numbers:
                    errors.append(
                        f"{task_name}: Dependencies references unknown T{dependency}"
                    )
                elif dependency >= number:
                    errors.append(
                        f"{task_name}: Dependencies may reference only earlier tasks; "
                        f"found T{dependency}"
                    )

        if not _is_meaningful(heading):
            errors.append(f"{task_name}: task title must be concrete")

    return errors


def validate_plan(
    markdown: str,
    *,
    repo_root: Path | None = None,
) -> list[str]:
    """Return all validation diagnostics for a Fable plan.

    An empty list means the plan is valid. ``repo_root`` is optional; when
    supplied, Files entries that resolve to existing directories are rejected.
    """
    sections, errors = _split_sections(markdown)
    missing_sections = [
        section for section in REQUIRED_SECTIONS if section not in sections
    ]
    errors.extend(
        f"missing required section '## {section}'"
        for section in missing_sections
    )
    if missing_sections:
        return errors

    errors.extend(_validate_metadata(sections))
    errors.extend(_validate_tasks(sections["Tasks (ordered)"], repo_root))
    return errors


def validate_plan_file(
    path: Path,
    *,
    repo_root: Path | None = None,
) -> list[str]:
    """Read and validate a Markdown plan file."""
    try:
        markdown = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"cannot read plan {path}: {exc}") from exc
    return validate_plan(markdown, repo_root=repo_root)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Validate an approved Fable implementation plan."
    )
    parser.add_argument("plan", type=Path, help="Markdown plan file to validate")
    parser.add_argument(
        "--repo",
        type=Path,
        default=Path.cwd(),
        help="repository root used to reject directory entries (default: cwd)",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command-line validator and return a process exit status."""
    args = parse_args(argv)
    try:
        errors = validate_plan_file(args.plan, repo_root=args.repo.resolve())
    except ValueError as exc:
        print(f"plan validation error: {exc}", file=sys.stderr)
        return 2

    if errors:
        print(
            f"plan validation failed with {len(errors)} violation(s):",
            file=sys.stderr,
        )
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    print(f"plan validation passed: {args.plan}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
