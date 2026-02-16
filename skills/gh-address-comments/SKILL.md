---
name: gh-address-comments
description: Help address review/issue comments on the open GitHub PR for the current branch using gh CLI; verify gh auth first and prompt the user to authenticate if not logged in.
metadata:
  short-description: Address comments in a GitHub PR review
---

# PR Comment Handler

Guide to find the open PR for the current branch and address its comments with gh CLI.

Prereq: ensure `gh` is authenticated (for example, run `gh auth login` once), then run `gh auth status` so `gh` commands succeed. If auth checks fail, prompt the user to re-authenticate and retry.

## 1) Inspect comments needing attention
- Run `python3 <skill-root>/scripts/fetch_comments.py` to print all comments and review threads on the PR
- Reporting input is pre-filtered:
  - Skip resolved review threads
  - Skip top-level conversation comments authored by bots

## 2) Plan this round automatically
- Number all the review threads and comments and provide a short summary of what would be required to apply each fix
- By default, address all unresolved comments in this round without asking the user to choose
- Ask the user only when there is a hard blocker or a risky product decision that cannot be inferred

## 3) Apply fixes
- Apply fixes for all comments selected by the default rule
- When committing during this workflow, invoke the `git-commit` skill rather than composing `git commit` commands ad hoc.
- If a commit is needed, follow the commit format from `git-commit` skill:
  - Use a Conventional Commit subject (`type(scope): summary`)
  - Validate message text first:
    - `python3 <repo-root>/skills/git-commit/scripts/validate_commit_message.py --subject "<subject>" --body-line "<line>"`
  - Commit with repeated `-m` flags (one per paragraph/line)
  - Never embed literal escaped control tokens (for example `\\n`, `\\r`,
    `\\t`) in commit text
- In iterative review loops, do not post thread replies by default
- Report what was changed and which thread IDs are likely addressed

## 4) Only when user explicitly asks to reply
- Draft each PR reply in a heredoc or file and validate before posting:
  - `python3 <skill-root>/scripts/validate_reply_body.py --body-file <path>`
  - or `python3 <skill-root>/scripts/validate_reply_body.py --body-file -`
- Write replies in reviewer-facing language (for example: "Thanks, addressed in the latest patch" and what changed).
- Do not paste git commit messages into PR replies (for example: imperative summary + bullet list changelog format).
- Post validated replies with `gh` using `--body-file` to preserve newlines
  and avoid literal escape sequences (for example `\\n`)

Notes:
- If gh hits auth/rate issues mid-run, prompt the user to re-authenticate with `gh auth login`, then retry.
- Do not post reply text that fails validation.
- Default workflow: fix code and push first; reply to threads only on request.
