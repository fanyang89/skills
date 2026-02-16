#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
import re
import shlex
import subprocess
import sys
import textwrap
from types import ModuleType

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


def _load_validator_module() -> ModuleType:
    validator_path = (
        Path(__file__).resolve().parents[2]
        / "git-commit"
        / "scripts"
        / "validate_commit_message.py"
    )
    spec = importlib.util.spec_from_file_location(
        "shared_commit_validator",
        validator_path,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load validator: {validator_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


VALIDATOR = _load_validator_module()
PASTE_MARKERS = getattr(VALIDATOR, "PASTE_MARKERS")
CONVENTIONAL_SUBJECT_RE = getattr(VALIDATOR, "CONVENTIONAL_SUBJECT_RE")


def _validate_message(subject: str, body_lines: list[str]) -> tuple[list[str], list[str]]:
    return VALIDATOR.validate_commit_message(subject, body_lines)


def _normalize_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _split_message(raw_message: str) -> tuple[str, list[str]]:
    lines = raw_message.replace("\r\n", "\n").split("\n")
    while lines and not lines[0].strip():
        lines.pop(0)
    if not lines:
        return "", []

    subject = lines[0].strip()
    body_lines = lines[1:]
    while body_lines and not body_lines[-1].strip():
        body_lines.pop()
    return subject, body_lines


def _extract_paragraphs(lines: list[str]) -> list[list[str]]:
    paragraphs: list[list[str]] = []
    current: list[str] = []
    for line in lines:
        if line.strip():
            current.append(line)
            continue
        if current:
            paragraphs.append(current)
            current = []
    if current:
        paragraphs.append(current)
    return paragraphs


def _normalize_subject(subject: str) -> str:
    cleaned = _normalize_spaces(subject)
    if CONVENTIONAL_SUBJECT_RE.match(cleaned):
        if len(cleaned) <= 72:
            return cleaned
        return textwrap.shorten(cleaned, width=72, placeholder="...")

    tail = cleaned
    if ":" in cleaned:
        tail = cleaned.split(":", 1)[1].strip() or cleaned
    tail = re.sub(r"^[^A-Za-z0-9]+", "", tail)
    tail = textwrap.shorten(tail, width=58, placeholder="...")
    if not tail:
        tail = "reword malformed commit message"

    candidate = f"chore: {tail}"
    if len(candidate) > 72:
        candidate = textwrap.shorten(candidate, width=72, placeholder="...")
    return candidate


def _build_candidate(raw_message: str) -> tuple[str, str, str, list[str]]:
    normalized = raw_message.replace("\r\n", "\n")
    normalized = normalized.replace("\\n", "\n").replace("\\r", "\n")
    normalized = normalized.replace("\\t", " ")

    for marker in PASTE_MARKERS:
        normalized = re.sub(re.escape(marker), "", normalized, flags=re.IGNORECASE)

    subject, body_lines = _split_message(normalized)
    subject = _normalize_subject(subject)

    paragraphs = _extract_paragraphs(body_lines)
    prose_paragraphs: list[str] = []
    bullets: list[str] = []

    for paragraph in paragraphs:
        prose_lines: list[str] = []
        for line in paragraph:
            stripped = line.strip()
            bullet_match = BULLET_PREFIX_RE.match(stripped)
            if bullet_match:
                bullets.append(_normalize_spaces(bullet_match.group(1)))
            else:
                prose_lines.append(stripped)

        if prose_lines:
            prose_paragraphs.append(_normalize_spaces(" ".join(prose_lines)))

    summary_source = (
        prose_paragraphs[0]
        if prose_paragraphs
        else "Reword commit message formatting to match repository policy."
    )
    summary_paragraph = textwrap.fill(summary_source, width=72)

    if not bullets:
        for prose in prose_paragraphs[1:]:
            for sentence in re.split(r"(?<=[.!?])\s+", prose):
                cleaned = _normalize_spaces(sentence.strip("- "))
                if cleaned:
                    bullets.append(cleaned)
            if len(bullets) >= 6:
                break

    if not bullets:
        bullets = [
            "Align message formatting with shared commit policy.",
            "Use repeated -m flags and avoid escaped newline tokens.",
        ]

    deduped: list[str] = []
    seen: set[str] = set()
    for bullet in bullets:
        cleaned = _normalize_spaces(bullet)
        if not cleaned:
            continue
        lowered = cleaned.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        deduped.append(cleaned)

    wrapped_bullet_lines: list[str] = []
    for bullet in deduped[:6]:
        wrapped = textwrap.fill(
            bullet,
            width=72,
            initial_indent="- ",
            subsequent_indent="  ",
        )
        wrapped_bullet_lines.extend(wrapped.splitlines())

    bullet_paragraph = "\n".join(wrapped_bullet_lines)
    body_lines_candidate = summary_paragraph.splitlines() + [""] + wrapped_bullet_lines
    return subject, summary_paragraph, bullet_paragraph, body_lines_candidate


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


def _check_commits(
    base_ref: str,
) -> tuple[list[str], list[tuple[str, str, list[str], list[str]]]]:
    commits = _get_commits(base_ref)
    invalid: list[tuple[str, str, list[str], list[str]]] = []

    for sha in commits:
        raw = _get_message(sha)
        subject, body_lines = _split_message(raw)
        errors, warnings = _validate_message(subject, body_lines)
        if errors:
            invalid.append((sha, subject or "<empty>", errors, warnings))

    return commits, invalid


def _fix_current_head() -> int:
    short_sha = _git_output("rev-parse", "--short", "HEAD").strip()
    raw = _get_message("HEAD")
    subject, body_lines = _split_message(raw)
    errors, warnings = _validate_message(subject, body_lines)

    if not errors:
        print(f"[{short_sha}] commit message already valid")
        if warnings:
            for warning in warnings:
                print(f"[{short_sha}] warning: {warning}")
        return 0

    print(f"[{short_sha}] invalid commit message; rewording")
    for issue in errors:
        print(f"- {issue}")

    new_subject, new_summary, new_bullets, new_body_lines = _build_candidate(raw)
    new_errors, _ = _validate_message(new_subject, new_body_lines)
    if new_errors:
        print(f"[{short_sha}] unable to build valid replacement", file=sys.stderr)
        for issue in new_errors:
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
    print(f"[{short_sha}] amended")
    return 0


def _has_local_changes() -> bool:
    return bool(_git_output("status", "--porcelain").strip())


def _has_merge_commits(base_ref: str) -> bool:
    return bool(_git_output("rev-list", "--merges", f"{base_ref}..HEAD").strip())


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
            "merge commits detected in range; automatic reword only supports "
            "linear commit ranges",
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
    for sha, subject, errors, warnings in invalid:
        print(f"- {sha[:12]} {subject}")
        for issue in errors:
            print(f"  - {issue}")
        for warning in warnings:
            print(f"  - warning: {warning}")

    if not args.apply:
        print("\nre-run with --apply to auto-reword invalid commits")
        return 1

    apply_result = _apply_reword(base_ref)
    if apply_result != 0:
        return apply_result

    _, invalid_after = _check_commits(base_ref)
    if invalid_after:
        print(
            f"rewording finished but {len(invalid_after)} invalid commit(s) remain",
            file=sys.stderr,
        )
        for sha, subject, errors, warnings in invalid_after:
            print(f"- {sha[:12]} {subject}", file=sys.stderr)
            for issue in errors:
                print(f"  - {issue}", file=sys.stderr)
            for warning in warnings:
                print(f"  - warning: {warning}", file=sys.stderr)
        return 7

    print("all commit messages are now valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
