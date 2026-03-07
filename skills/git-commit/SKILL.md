---
name: git-commit
description: Generate Conventional Commits messages and run git add/git commit from current repo changes. Use when the user says "git commit" or asks to auto-stage changes and craft a commit message from the diff.
---

# Git Commit Agent

## Overview

Create a Conventional Commits message based on the current staged diff, then perform `git commit` after auto-staging relevant changes (excluding obvious temp files).

## Workflow

1. Check for already-staged changes.
   - Run `git diff --cached --name-status`.
   - If staged files exist, skip staging and proceed to inspection/commit using the staged set.
2. Stage changes when nothing is staged.
   - Run the staging script from this skill: `python3 <skill-root>/scripts/stage_changes.py`
   - The script stages tracked changes (`git add -u`) and selectively stages untracked files that are not ignored and not temporary.
   - If nothing is staged after running, stop and report that there are no relevant changes to commit.

3. Inspect staged changes.
   - Use `git diff --cached --name-status` to understand file-level changes.
   - Use `git diff --cached` to spot functional changes and key behaviors.

4. Compose a Conventional Commits message.
    - Follow repository policy in `AGENTS.md` and enforce it with `scripts/validate_commit_message.py`.
    - Format:
      - Title line: `type(scope): short summary`
      - Body: prefer a brief summary first, then 1-6 bullet points.
      - Bullet lines must start with `- `.
    - Choose `type` by best fit:
      - `feat`: new user-facing functionality
      - `fix`: bug fixes or behavior corrections
      - `refactor`: internal change without behavior change
      - `docs`: documentation-only change
      - `test`: tests-only change
      - `build`, `ci`, `chore`, `perf`, `style`, `revert` as appropriate
    - Choose `scope` from the most relevant top-level area (examples: `core`, `raftor`, `wal`, `rpc`, `tests`, `docs`, `build`). Omit scope if unclear.
    - Keep the title on one line and under 72 characters.
    - Hard-wrap body text at column 72 using word boundaries.
    - Avoid splitting words across lines and prefer wrapping at spaces.
    - Avoid trailing period in the title summary.

5. Validate the generated commit message.
    - Run the validation script before committing:
      - `python3 <skill-root>/scripts/validate_commit_message.py --subject "type(scope): summary" --body-line "Brief summary of why this change was made." --body-line "- bullet one" --body-line "- bullet two"`
    - If validation fails, regenerate/fix the message and validate again.
    - Treat escaped control tokens as hard failures (for example `\\n`, `\\r`, `\\t`).
    - Treat body-structure hints as warnings; prefer fixing them before commit.

6. Commit without prompting for confirmation.
    - Always use repeated `-m` flags with one paragraph per flag.
    - Use one `-m` for the subject, one for the summary paragraph, and one for
      the full bullet block.
    - Keep bullet items contiguous inside the bullet-block paragraph (no blank
      lines between bullet items).
    - Example:
      ```bash
      git commit -m "type(scope): summary\n\nBrief summary of why this change was made.\n- bullet one\n- bullet two"
      ```
    - Do not run `git commit` without `-m` and do not open an interactive editor for commit message entry.

## Notes

- Do not include obvious temporary or generated files (e.g., editor swap files, build outputs, caches).
- Prefer clarity over cleverness in the summary and bullets; mention key files if it helps understanding.
- Validation rejects paste artifacts (for example `[Pasted`, `[200~`, `[201~`), ANSI escape sequences, control characters, and escaped control tokens in the message.

## Resources

### scripts/

- `stage_changes.py`: stage tracked changes and select untracked files while skipping temp-like paths.
- `validate_commit_message.py`: validate generated subject/body lines and fail fast on malformed or polluted message content.
