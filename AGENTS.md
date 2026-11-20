# AI Agent Instructions

This project uses `.ai-sync/` for cross-platform AI agent synchronization.

## On Start
1. Read `.ai-sync/HANDOFF.md` — current state, what was done, what's next
2. Read `.ai-sync/PROGRESS.md` — completed vs pending tasks
3. Read `.ai-sync/PLAN.md` — the implementation plan (do not deviate)

## During Work
- Check off completed tasks in PROGRESS.md
- Match existing code patterns

## On Stop
1. Update `HANDOFF.md` with: completed work, specific next steps, files changed, build status
2. Update `PROGRESS.md` with completed items
3. Run verification (build + typecheck) before stopping

## Rules
1. Follow the plan — no unplanned features or refactors
2. Don't repeat work — check PROGRESS.md first
3. Be specific in handoffs — actionable next steps required
4. Run verification before stopping
5. Document decisions — the next agent has zero context
