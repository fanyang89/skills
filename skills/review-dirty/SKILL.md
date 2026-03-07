---
name: review-dirty
description: Review dirty code changes. Use when user asks to "review",
  "review changes", or "review dirty code".
metadata:
  short-description: Review dirty repo changes
---

# Review Dirty Changes

Review uncommitted repo changes without modifying files unless the user asks.

## Rules

- Treat all dirty changes as likely from the current session, but do not assume.
- Do not modify anything unless explicitly told to do so.
- The final user-facing review response must be in Chinese.

## Workflow

1. If you are Codex:
   - Review dirty repo changes directly.
   - Ignore the delegation flow below.
   - Inspect at least:
     - `git status --short`
     - `git diff --cached`
     - `git diff`
   - Return a concise review with:
     - critical issues first
     - file references
     - concrete fix suggestions
   - Write the final review response in Chinese.

2. If you are not Codex:
   - Run this command with Bash tool:
     - `codex exec "Do not modify anything unless I tell you to. Review the dirty repo changes which are to implement: <prompt>" $ARGUMENTS`
   - Pass through the original user prompt in `<prompt>`.
   - Set timeout to at least 10 minutes (600000 ms).
   - Convert the final review output to Chinese before replying.
   - Keep file paths, symbols, and code identifiers unchanged.
