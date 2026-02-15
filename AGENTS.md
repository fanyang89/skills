## Git Commit Message Policy

When creating a commit message, wrap text at column 72 using word boundaries.

- Subject line: keep it on one line and under 72 characters.
- Body text: hard-wrap at column 72.
- Body structure: write a brief summary first, then use bullet points.
- Bullets: use `- ` prefixes and keep each bullet focused.
- Do not split a word across lines.
- Prefer wrapping at spaces so each line remains readable.

Example:

```text
feat(parser): improve error context for nested config blocks

Add line-level location hints for nested parsing failures and include
the closest parent key in the error output.

- Show parent key context for nested parser errors.
- Improve readability of error output during config debugging.
```
