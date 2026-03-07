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
    r"(?:\([^)]+\))?!?:\s+\S",
    re.IGNORECASE,
)
REVIEWER_FACING_RE = re.compile(
    r"\b(thanks|thank you|good catch|addressed|resolved|fixed|updated|"
    r"follow-up|follow up|i|we)\b",
    re.IGNORECASE,
)
IMPERATIVE_PREFIXES = (
    "add ",
    "avoid ",
    "change ",
    "clean up ",
    "create ",
    "drop ",
    "ensure ",
    "fix ",
    "implement ",
    "improve ",
    "keep ",
    "make ",
    "move ",
    "refactor ",
    "remove ",
    "rename ",
    "replace ",
    "set ",
    "simplify ",
    "update ",
    "use ",
)


def _starts_with_imperative(text: str) -> bool:
    lowered = text.strip().lower()
    return any(lowered.startswith(prefix) for prefix in IMPERATIVE_PREFIXES)


def looks_like_commit_message(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False

    first_non_empty_line = next(
        (line.strip() for line in stripped.splitlines() if line.strip()),
        "",
    )
    if CONVENTIONAL_SUBJECT_RE.match(first_non_empty_line):
        return True

    paragraphs = [
        paragraph.strip()
        for paragraph in re.split(r"\n\s*\n", stripped)
        if paragraph.strip()
    ]
    if len(paragraphs) < 2:
        return False

    trailing_lines = [
        line.strip()
        for line in "\n\n".join(paragraphs[1:]).splitlines()
        if line.strip()
    ]
    if not trailing_lines or not all(line.startswith("- ") for line in trailing_lines):
        return False

    if REVIEWER_FACING_RE.search(stripped):
        return False

    intro = paragraphs[0]
    intro_lower = intro.lower()
    bullet_imperative_count = sum(
        1
        for line in trailing_lines
        if _starts_with_imperative(line[2:].lstrip())
    )

    if _starts_with_imperative(intro):
        return True
    if intro_lower.startswith((
        "this change ",
        "this updates ",
        "this adds ",
        "this fixes ",
    )):
        return True
    if len(trailing_lines) >= 2 and bullet_imperative_count == len(trailing_lines):
        return True

    return False


def find_issues(text: str) -> list[str]:
    issues: list[str] = []
    text_lower = text.lower()

    for marker in PASTE_MARKERS:
        if marker in text_lower:
            issues.append(f"body contains paste marker '{marker}'")

    if ANSI_ESCAPE_RE.search(text):
        issues.append("body contains ANSI escape sequence")

    if CONTROL_CHAR_RE.search(text):
        issues.append("body contains control character")

    escaped_sequences = sorted(set(ESCAPED_SEQUENCE_RE.findall(text)))
    if escaped_sequences:
        joined = ", ".join(f"'{sequence}'" for sequence in escaped_sequences)
        issues.append(f"body contains escaped sequence {joined}")

    if looks_like_commit_message(text):
        issues.append(
            "body looks like a git commit message; write a reviewer-facing "
            "reply instead"
        )

    return issues


def read_body(body: str | None, body_file: str | None) -> str:
    if body is not None:
        return body
    if body_file == "-":
        return sys.stdin.read()
    if body_file:
        with open(body_file, "r", encoding="utf-8") as handle:
            return handle.read()
    return ""


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate generated PR reply text."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--body", help="Reply body text")
    group.add_argument(
        "--body-file",
        help="Path to reply body file, or '-' to read from stdin",
    )
    args = parser.parse_args()

    body = read_body(args.body, args.body_file)
    issues = find_issues(body)

    if issues:
        print("PR reply validation failed:", file=sys.stderr)
        for issue in issues:
            print(f"- {issue}", file=sys.stderr)
        return 1

    print("PR reply validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
