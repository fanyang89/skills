#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import shlex
import subprocess
import sys
import textwrap

PASTE_MARKERS = (
    "[pasted",
    "pasted ~",
    "[200~",
    "[201~",
)

ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")
CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
ESCAPED_SEQUENCE_RE = re.compile(r"\\[nrt]")
BULLET_PREFIX_RE = re.compile(r"^[-*•]\s+(.*)$")


def _run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if check and proc.returncode != 0:
        stderr = proc.stderr.strip()
        raise RuntimeError(f"command failed: {' '.join(cmd)}\n{stderr}")
    return proc


def _git_output(*args: str) -> str:
    return _run(["git", *args]).stdout


def _git_ok(*args: str) -> bool:
    return _run(["git", *args], check=False).returncode == 0


def _normalize_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _split_message(raw_message: str) -> tuple[str, str]:
    lines = raw_message.splitlines()
    if not lines:
        return "", ""

    first_non_empty = 0
    while first_non_empty < len(lines) and not lines[first_non_empty].strip():
        first_non_empty += 1

    if first_non_empty >= len(lines):
        return "", ""

    subject = lines[first_non_empty].strip()
    body = "\n".join(lines[first_non_empty + 1 :]).strip("\n")
    return subject, body


def _find_line_issues(label: str, text: str, check_width: bool) -> list[str]:
    issues: list[str] = []
    lowered = text.lower()

    for marker in PASTE_MARKERS:
        if marker in lowered:
            issues.append(f"{label} contains paste marker '{marker}'")

    if ANSI_ESCAPE_RE.search(text):
        issues.append(f"{label} contains ANSI escape sequence")

    if CONTROL_CHAR_RE.search(text):
        issues.append(f"{label} contains control character")

    escaped = sorted(set(ESCAPED_SEQUENCE_RE.findall(text)))
    if escaped:
        joined = ", ".join(f"'{item}'" for item in escaped)
        issues.append(f"{label} contains escaped sequence {joined}")

    if check_width and text and len(text) > 72:
        issues.append(f"{label} exceeds 72 columns ({len(text)})")

    return issues


def _validate_structure(body: str) -> list[str]:
    issues: list[str] = []
    if not body.strip():
        issues.append("body is required and must include summary + bullet list")
        return issues

    paragraphs = [
        paragraph.strip()
        for paragraph in re.split(r"\n\s*\n", body.strip())
        if paragraph.strip()
    ]
    if len(paragraphs) < 2:
        issues.append("body must contain a summary paragraph followed by bullets")
        return issues

    summary_lines = [line.strip() for line in paragraphs[0].splitlines() if line.strip()]
    if not summary_lines:
        issues.append("summary paragraph is empty")
    elif all(line.startswith("- ") for line in summary_lines):
        issues.append("summary paragraph must not be a bullet list")

    bullet_lines: list[str] = []
    for paragraph in paragraphs[1:]:
        for line in paragraph.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            bullet_lines.append(stripped)
            if not stripped.startswith("- ") and not line.startswith("  "):
                issues.append(
                    "all lines after summary must be bullets or wrapped bullet lines"
                )

    if not bullet_lines:
        issues.append("at least one bullet is required after the summary")

    return issues


def validate_commit_message(subject: str, body: str) -> list[str]:
    issues: list[str] = []
    if not subject:
        return ["subject is empty"]

    if "\n" in subject or "\r" in subject:
        issues.append("subject must be a single line")
    issues.extend(_find_line_issues("subject", subject, check_width=True))

    for index, line in enumerate(body.splitlines(), start=1):
        issues.extend(
            _find_line_issues(
                f"body line {index}",
                line,
                check_width=bool(line.strip()),
            )
        )

    issues.extend(_validate_structure(body))
    return issues


def _extract_paragraphs(text: str) -> list[str]:
    return [
        paragraph.strip()
        for paragraph in re.split(r"\n\s*\n", text.strip())
        if paragraph.strip()
    ]


def _build_candidate(raw_message: str) -> tuple[str, str, str, str]:
    normalized = raw_message.replace("\r\n", "\n")
    normalized = normalized.replace("\\n", "\n").replace("\\t", " ")

    for marker in PASTE_MARKERS:
        normalized = re.sub(re.escape(marker), "", normalized, flags=re.IGNORECASE)

    subject, body = _split_message(normalized)
    subject = _normalize_spaces(subject)
    if not subject:
        subject = "chore: reword malformed commit message"
    if len(subject) > 72:
        subject = textwrap.shorten(subject, width=72, placeholder="...")

    paragraphs = _extract_paragraphs(body)
    prose_paragraphs: list[str] = []
    bullets: list[str] = []

    for paragraph in paragraphs:
        lines = [line.strip() for line in paragraph.splitlines() if line.strip()]
        prose_lines: list[str] = []

        for line in lines:
            bullet_match = BULLET_PREFIX_RE.match(line)
            if bullet_match:
                bullets.append(_normalize_spaces(bullet_match.group(1)))
            else:
                prose_lines.append(line)

        if prose_lines:
            prose_paragraphs.append(_normalize_spaces(" ".join(prose_lines)))

    summary_source = (
        prose_paragraphs[0]
        if prose_paragraphs
        else "Reword commit message formatting to match repository policy."
    )
    summary_paragraph = textwrap.fill(summary_source, width=72)

    if not bullets:
        for extra in prose_paragraphs[1:]:
            for sentence in re.split(r"(?<=[.!?])\s+", extra):
                cleaned = _normalize_spaces(sentence.strip("- "))
                if cleaned:
                    bullets.append(cleaned)
            if len(bullets) >= 6:
                break

    if not bullets:
        bullets = [
            "Align message structure with the repository commit policy.",
            "Use wrapped body text and explicit bullet points.",
        ]

    deduped: list[str] = []
    seen: set[str] = set()
    for bullet in bullets:
        cleaned = _normalize_spaces(bullet)
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(cleaned)

    wrapped_lines: list[str] = []
    for bullet in deduped[:6]:
        wrapped = textwrap.fill(
            bullet,
            width=72,
            initial_indent="- ",
            subsequent_indent="  ",
        )
        wrapped_lines.extend(wrapped.splitlines())

    bullet_paragraph = "\n".join(wrapped_lines)
    body_text = f"{summary_paragraph}\n\n{bullet_paragraph}".strip()
    return subject, summary_paragraph, bullet_paragraph, body_text


def _resolve_base_ref(explicit_base: str | None) -> str:
    if explicit_base:
        return explicit_base

    gh_proc = _run(
        ["gh", "pr", "view", "--json", "baseRefName", "--jq", ".baseRefName"],
        check=False,
    )
    if gh_proc.returncode == 0:
        base_name = gh_proc.stdout.strip()
        if base_name:
            for candidate in (f"origin/{base_name}", base_name):
                if _git_ok("rev-parse", "--verify", candidate):
                    return candidate

    for candidate in ("origin/main", "main", "origin/master", "master"):
        if _git_ok("rev-parse", "--verify", candidate):
            return candidate

    raise RuntimeError(
        "unable to resolve base branch; provide one with --base <ref>"
    )


def _get_commits(base_ref: str) -> list[str]:
    if not _git_ok("merge-base", base_ref, "HEAD"):
        raise RuntimeError(f"unable to compute merge-base between {base_ref} and HEAD")
    output = _git_output("rev-list", "--reverse", f"{base_ref}..HEAD")
    return [line.strip() for line in output.splitlines() if line.strip()]


def _get_message(commit_sha: str) -> str:
    return _git_output("show", "-s", "--format=%B", commit_sha)


def _check_commits(base_ref: str) -> tuple[list[str], list[tuple[str, str, list[str]]]]:
    commits = _get_commits(base_ref)
    invalid: list[tuple[str, str, list[str]]] = []

    for sha in commits:
        raw = _get_message(sha)
        subject, body = _split_message(raw)
        issues = validate_commit_message(subject, body)
        if issues:
            invalid.append((sha, subject or "<empty>", issues))

    return commits, invalid


def _fix_current_head() -> int:
    current_sha = _git_output("rev-parse", "--short", "HEAD").strip()
    raw = _get_message("HEAD")
    subject, body = _split_message(raw)
    issues = validate_commit_message(subject, body)

    if not issues:
        print(f"[{current_sha}] commit message already valid")
        return 0

    print(f"[{current_sha}] invalid commit message; rewording")
    for issue in issues:
        print(f"- {issue}")

    new_subject, new_summary, new_bullets, new_body = _build_candidate(raw)
    candidate_issues = validate_commit_message(new_subject, new_body)
    if candidate_issues:
        print(f"[{current_sha}] unable to build valid replacement", file=sys.stderr)
        for issue in candidate_issues:
            print(f"- {issue}", file=sys.stderr)
        return 2

    _run(
        [
            "git",
            "commit",
            "--amend",
            "-m",
            new_subject,
            "-m",
            new_summary,
            "-m",
            new_bullets,
        ]
    )
    print(f"[{current_sha}] amended")
    return 0


def _has_local_changes() -> bool:
    status = _git_output("status", "--porcelain")
    return bool(status.strip())


def _has_merge_commits(base_ref: str) -> bool:
    merges = _git_output("rev-list", "--merges", f"{base_ref}..HEAD")
    return bool(merges.strip())


def _apply_reword(base_ref: str) -> int:
    if _has_local_changes():
        print(
            "working tree is not clean; stash or commit local changes before "
            "running --apply",
            file=sys.stderr,
        )
        return 4

    if _has_merge_commits(base_ref):
        print(
            "merge commits detected in range; automatic non-interactive reword "
            "only supports linear commit ranges",
            file=sys.stderr,
        )
        return 5

    script_path = shlex.quote(__file__)
    python_bin = shlex.quote(sys.executable)
    exec_cmd = f"{python_bin} {script_path} --fix-current-head"
    proc = _run(["git", "rebase", base_ref, "--exec", exec_cmd], check=False)

    if proc.returncode != 0:
        stdout = (proc.stdout or "").strip()
        stderr = (proc.stderr or "").strip()
        if stdout:
            print(stdout, file=sys.stderr)
        if stderr:
            print(stderr, file=sys.stderr)
        print(
            "rebase failed; resolve conflicts then continue with `git rebase "
            "--continue`, or abort with `git rebase --abort`",
            file=sys.stderr,
        )
        return 6

    print("reword pass completed")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate commit messages in base..HEAD and optionally reword "
            "invalid commits."
        )
    )
    parser.add_argument(
        "--base",
        help="Base branch/ref for commit range (default: infer from PR/main)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Automatically reword invalid commits in the range",
    )
    parser.add_argument(
        "--fix-current-head",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    args = parser.parse_args()

    if args.fix_current_head:
        return _fix_current_head()

    try:
        _git_output("rev-parse", "--verify", "HEAD")
        base_ref = _resolve_base_ref(args.base)
        commits, invalid = _check_commits(base_ref)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if not commits:
        print(f"no commits found in {base_ref}..HEAD")
        return 0

    print(f"checked {len(commits)} commits in range {base_ref}..HEAD")
    if not invalid:
        print("all commit messages are valid")
        return 0

    print(f"found {len(invalid)} invalid commit message(s):")
    for sha, subject, issues in invalid:
        print(f"- {sha[:12]} {subject}")
        for issue in issues:
            print(f"  - {issue}")

    if not args.apply:
        print("\nre-run with --apply to auto-reword invalid commits")
        return 1

    apply_result = _apply_reword(base_ref)
    if apply_result != 0:
        return apply_result

    commits_after, invalid_after = _check_commits(base_ref)
    if invalid_after:
        print(
            f"rewording finished but {len(invalid_after)} invalid commit(s) remain",
            file=sys.stderr,
        )
        for sha, subject, issues in invalid_after:
            print(f"- {sha[:12]} {subject}", file=sys.stderr)
            for issue in issues:
                print(f"  - {issue}", file=sys.stderr)
        return 7

    print(f"all {len(commits_after)} commit messages are now valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
