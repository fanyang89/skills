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

    if check_width and text and len(text) > 72:
        issues.append(f"{label} exceeds 72 columns ({len(text)})")

    return issues


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

    issues: list[str] = []

    if "\n" in args.subject or "\r" in args.subject:
        issues.append("subject must be a single line")

    issues.extend(find_issues("subject", args.subject, check_width=True))

    for index, line in enumerate(args.body_line, start=1):
        issues.extend(
            find_issues(f"body line {index}", line, check_width=bool(line.strip()))
        )

    if issues:
        print("Commit message validation failed:", file=sys.stderr)
        for issue in issues:
            print(f"- {issue}", file=sys.stderr)
        return 1

    print("Commit message validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
