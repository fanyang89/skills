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
