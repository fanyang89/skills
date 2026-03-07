---
name: git-reword
description: Reword or amend the current HEAD commit message in a Git repo. Use when the user asks to "reword git HEAD", "amend the last commit message", or "change the most recent commit message".
---

# Git Reword HEAD

## Goal

Reword the latest commit message safely, without unintentionally altering the commit contents.

## Workflow

1. Verify there is a HEAD commit.
   - Run `git rev-parse --verify HEAD`.
   - If it fails, stop and report that there is no commit to amend.

2. Check repo state.
   - Run `git status -sb`.
   - If there are staged changes, warn that `git commit --amend` will include them.
     - Offer to unstage with `git reset` or proceed as-is.

3. Show the current HEAD message for context.
   - Run `git log -1 --pretty=%s` for the subject line.
   - Run `git log -1 --pretty=%B` for the full message when needed.

4. Collect the new commit message from the user.
   - Follow the commit message format and rules from the `git-commit` skill.
   - Ask for the required parts (type/scope/summary, body bullets) as needed.

5. Validate the new commit message.
     - Run the validator from the `git-commit` skill before amend:
       - `python3 <repo-root>/skills/git-commit/scripts/validate_commit_message.py --subject "<subject>" --body-line "<body line 1>" --body-line "<body line 2>"`
     - If validation fails, regenerate/fix the message and validate again.
     - Escaped control tokens (for example `\\n`, `\\r`, `\\t`) are hard
       failures and must be removed before amend.

6. Amend the commit message.
    - Use repeated `-m` flags with one paragraph per flag.
    - Use one `-m` for the subject, one for the summary paragraph, and one for
      the full bullet block.
    - Keep bullet items contiguous in the bullet-block paragraph (no blank
      lines between bullet items).
    - Example:
      ```bash
      git commit --amend -m "<subject>" \
        -m "<summary paragraph>" \
        -m "- bullet one
- bullet two"
      ```
    - Do not run `git commit --amend` without `-m` and do not open an
      interactive editor for commit message entry.

7. If the commit was already pushed, warn before any push.
    - Explain that rewriting history requires `git push --force-with-lease`.
    - Do not push unless the user explicitly asks.

## Notes

- Keep the subject on one line and under 72 characters.
- Avoid amending if the user is unsure about staged changes; resolve staging first.
