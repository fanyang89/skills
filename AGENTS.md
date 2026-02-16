## Git Commit Message Policy

When creating a commit message, wrap text at column 72 using word boundaries.

- Subject line: keep it on one line and under 72 characters.
- Subject line: use Conventional Commits format `type(scope): summary`.
- Body text: hard-wrap at column 72.
- Body structure: prefer a brief summary first, then bullet points.
- Bullets: prefer `- ` prefixes and keep each bullet focused.
- When committing from CLI, pass subject/body with repeated `-m` flags.
- Do not put escaped control tokens (for example `\\n`, `\\r`, `\\t`) in
  commit text.
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
