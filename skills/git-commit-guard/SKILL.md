---
name: git-commit-guard
description: Check all commit messages in the current PR range and reword invalid ones automatically.
---

# Git Commit Guard

## Goal

Validate commit messages in the current PR range (`base..HEAD`) and reword
malformed commits automatically (for example, literal `\\n`, missing bullet
layout, or lines wider than 72 columns).

## Workflow

1. Resolve the commit range.
   - Prefer PR base branch from `gh pr view --json baseRefName`.
   - Fall back to local defaults (`origin/main`, `main`, `origin/master`,
     `master`) when PR metadata is unavailable.
   - Allow explicit override with `--base <ref>`.

2. Check all commit messages in the range.
   - Run:
     - `python3 <skill-root>/scripts/check_and_reword_pr_commits.py`
   - The script reuses the shared `git-commit` validator and applies the same
     policy everywhere:
     - subject must be one line and <= 72 chars;
     - subject must follow Conventional Commits format;
     - no paste artifacts, ANSI/control chars, or escaped control tokens
       (`\\n`, `\\r`, `\\t`).
   - Body-structure hints remain warnings (recommended but not blocking).

3. Reword invalid commits when needed.
   - Run:
     - `python3 <skill-root>/scripts/check_and_reword_pr_commits.py --apply`
   - This script:
     - validates all commits in `base..HEAD`;
     - detects malformed text patterns (for example `\\n`);
     - runs non-interactive `git rebase --exec`;
     - amends only invalid commits with repeated `-m` flags.

4. Verify the final commit messages.
   - Run:
     - `python3 <skill-root>/scripts/check_and_reword_pr_commits.py`
   - Report remaining invalid commits (if any).

## Notes

- Default to checking first, then auto-reword with `--apply`.
- Never push automatically; only push when the user explicitly asks.
- `--apply` requires a clean working tree and a linear commit range.
- If branch history changes after rewording, push with
  `git push --force-with-lease` only when the user asks.

## Resources

### scripts/

- `check_and_reword_pr_commits.py`: validate/reword commit messages across
  `base..HEAD`.
