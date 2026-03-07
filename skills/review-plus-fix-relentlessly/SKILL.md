---
name: review-plus-fix-relentlessly
description: >
  Review dirty code and fix iteratively.
  Use when user says "loop to fix dirty" or "review+fix".
metadata:
  short-description: Iterative review and fix loop
---

# Review Plus Fix Relentlessly

Review dirty repo changes and fix them in iterative cycles until no more
actionable issues remain.

## Rules

- All dirty repo changes are likely made in this session, though not always.
- Use the `review-dirty` skill to review current dirty changes each cycle.
- Fix findings to your best ability while matching repo preferences and style.
- Keep scope focused on dirty changes and directly related fixes.
- Do not commit or push unless the user explicitly asks.

## Workflow

1. Initialize loop state.
   - Set `cycles_done = 0`.
   - Set a conservative max-cycle guard (for example 10) to avoid endless loops.

2. Before each cycle, report cycle count.
   - Report: `Completed review+fix cycles: <cycles_done>`.

3. Run review.
   - Invoke `review-dirty` on the current dirty working tree.
   - Capture only actionable findings.

4. Stop check.
   - If no actionable findings remain, stop and report completion.
   - If findings repeat without meaningful progress across consecutive cycles,
     stop and report the likely blocker.

5. Apply fixes.
   - Implement fixes for the current cycle findings.
   - Prefer minimal, targeted edits unless a broader change is required.

6. Verify.
   - Run targeted checks relevant to touched code when available.
   - If checks fail, fix and re-verify within the same cycle.

7. Continue.
   - Increment `cycles_done += 1`.
   - Run `review-plus-fix-relentlessly` again for the next cycle.

## Output Per Cycle

- Cycle count report.
- Key findings from `review-dirty`.
- Fixes applied.
- Verification results.
- Continue/stop decision with reason.
