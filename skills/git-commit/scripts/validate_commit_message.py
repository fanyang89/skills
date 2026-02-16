#!/usr/bin/env python3
import argparse
import re
import sys

PASTE_MARKERS = (
    "[pasted",
    "pasted ~",
    "[200~",
    "[201~",
)

ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")
CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
ESCAPED_SEQUENCE_RE = re.compile(r"\\[nrt]")
CONVENTIONAL_SUBJECT_RE = re.compile(
    r"^(?:feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)"
    r"(?:\([^)]+\))?!?:\s+\S"
)


def find_issues(label: str, text: str, check_width: bool) -> list[str]:
    issues: list[str] = []
    text_lower = text.lower()

    for marker in PASTE_MARKERS:
        if marker in text_lower:
            issues.append(f"{label} contains paste marker '{marker}'")

    if ANSI_ESCAPE_RE.search(text):
        issues.append(f"{label} contains ANSI escape sequence")

    if CONTROL_CHAR_RE.search(text):
        issues.append(f"{label} contains control character")

    escaped_sequences = sorted(set(ESCAPED_SEQUENCE_RE.findall(text)))
    if escaped_sequences:
        joined = ", ".join(f"'{sequence}'" for sequence in escaped_sequences)
        issues.append(f"{label} contains escaped sequence {joined}")

    if check_width and text and len(text) > 72:
        issues.append(f"{label} exceeds 72 columns ({len(text)})")

    return issues


def _body_structure_warnings(body_lines: list[str]) -> list[str]:
    warnings: list[str] = []
    if not any(line.strip() for line in body_lines):
        warnings.append(
            "body should include a summary paragraph and bullet list"
        )
        return warnings

    paragraphs: list[list[str]] = []
    current: list[str] = []
    for line in body_lines:
        if line.strip():
            current.append(line)
            continue
        if current:
            paragraphs.append(current)
            current = []
    if current:
        paragraphs.append(current)

    if not paragraphs:
        warnings.append(
            "body should include a summary paragraph and bullet list"
        )
        return warnings

    first_paragraph = [line.strip() for line in paragraphs[0] if line.strip()]
    if first_paragraph and all(line.startswith("- ") for line in first_paragraph):
        warnings.append("body summary paragraph should appear before bullets")

    if len(paragraphs) < 2:
        warnings.append("body should include bullets after the summary paragraph")
        return warnings

    bullet_lines = [
        line
        for paragraph in paragraphs[1:]
        for line in paragraph
        if line.strip()
    ]
    if not bullet_lines:
        warnings.append("body should include bullets after the summary paragraph")
        return warnings

    if not any(line.strip().startswith("- ") for line in bullet_lines):
        warnings.append("body bullets should use '- ' prefixes")

    return warnings


def validate_commit_message(
    subject: str,
    body_lines: list[str],
) -> tuple[list[str], list[str]]:
    issues: list[str] = []
    warnings: list[str] = []

    if "\n" in subject or "\r" in subject:
        issues.append("subject must be a single line")

    issues.extend(find_issues("subject", subject, check_width=True))

    if not CONVENTIONAL_SUBJECT_RE.match(subject):
        issues.append(
            "subject must follow Conventional Commits format "
            "(type(scope): summary)"
        )

    for index, line in enumerate(body_lines, start=1):
        issues.extend(
            find_issues(f"body line {index}", line, check_width=bool(line.strip()))
        )

    warnings.extend(_body_structure_warnings(body_lines))
    return issues, warnings


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate generated commit message text."
    )
    parser.add_argument("--subject", required=True, help="Commit subject line")
    parser.add_argument(
        "--body-line",
        action="append",
        default=[],
        help="Body line (repeat for each line)",
    )
    args = parser.parse_args()

    issues, warnings = validate_commit_message(args.subject, args.body_line)

    if issues:
        print("Commit message validation failed:", file=sys.stderr)
        for issue in issues:
            print(f"- {issue}", file=sys.stderr)
        return 1

    if warnings:
        print("Commit message validation warnings:", file=sys.stderr)
        for warning in warnings:
            print(f"- {warning}", file=sys.stderr)

    print("Commit message validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
