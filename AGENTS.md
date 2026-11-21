# AI Agent Instructions

This project uses `.ai-sync/` for cross-platform AI agent synchronization.

## On Start
1. Run `git status` and `git pull --rebase` (on a clean tree). Note any modified files you did not touch; they belong to someone else.
2. Read `.ai-sync/HANDOFF.md` — current state, what was done, what's next, who owns the hardware
3. Read `.ai-sync/PROGRESS.md` — completed vs pending tasks
4. Read `.ai-sync/PLAN.md` — the implementation plan (do not deviate)

## During Work
- Check off completed tasks in PROGRESS.md
- Match existing code patterns
- Work on a branch, never directly on `main` (see Team Workflow)

## Commit Every Change
Nothing finished stays uncommitted. After each logical change (code, tests, docs, config or a fix), and before you report back:

1. Run verification: `python3 -m pytest tests/` and `bash -n cli.sh` (plus `py_compile` on changed Python).
2. Add an entry to `CHANGELOG.md` under `[Unreleased]`.
3. Stage explicit paths only: `git add <path> ...`. Never `git add -A` or `git add .`. The tree may hold someone else's work.
4. Commit with a Conventional Commits subject, one logical change per commit, e.g. `fix(elrobot): clamp goal to calibrated range`. Put the reason in the body.
5. Check with `git status`. Your files must be clean. Anything left is either someone else's (leave it) or a mistake (fix it).

Rules for what goes in a commit:
- Never commit `data/`, `logs/`, `station_data/`, `bin/`, `external/` (all gitignored) or secrets.
- Never commit another person's in-flight edit. Example: an uncommitted `config/elrobot.json` change is not yours to bundle. Ask, or commit only your own paths.
- If a pre-commit hook fails on files you did not write, report it and do not bypass it. Use `--no-verify` only when the failing check is provably outside your change, and say why in the commit body.
- Push only when asked.

## Post-Implementation Suggestions
After each implementation, give the user **3 suggestions** for the next steps in this project.
- Each must be **new**: not already done, and not already in `SUGGESTIONS.md`, `PROGRESS.md` or `PLAN.md`.
- Give each one a **priority** as a percentage and label: 90–100% Critical, 70–89% High value, 40–69% Nice to have, below 40% Optional. Order them most important first.
- Give each one a **category**: Professionalism, Security or Best practices.
- Explain each in plain English, for a reader who is not a specialist: **What** it is (one sentence), **Why** it matters (the benefit or the risk it removes), and **How** to do it (beginner-friendly steps).
- Record all 3 in `SUGGESTIONS.md` under the header `### Post-Implementation Suggestions` (create the file if it is missing). Status is `⏳ Unimplemented`, with a **Reason Deferred**. When a suggestion is implemented, delete its entry. Do not mark it done or keep an archive.
- Stage and commit `SUGGESTIONS.md` with the change it came from.

## Team Workflow
- **Branches:** `<type>/<area>-<short-slug>`, e.g. `fix/elrobot-goto-clamp`, `docs/agents-team-workflow`. Branch from an up-to-date `main`.
- **Merging:** open a pull request into `main` with `gh pr create`. Get one human review before merging. Keep PRs small: one feature or fix each.
- **Rebase, don't merge, your own branch:** `git pull --rebase origin main` before you push. Never force-push `main`. Force-push your own branch only after telling the team.
- **Hardware is single-writer:** only the person named as hardware owner in `HANDOFF.md` runs motion commands (`hw jog`, `hw goto`, `hw torque on`, `hw identify`). Others read only (`preflight`, `hw motors`, `logs`). Hand over by updating the owner line in `HANDOFF.md` and committing it.
- **Calibration values are committed by the person who measured them.** `config/elrobot.json` (thresholds, workspace, `measured` flag) and `config/waypoints.json` go in a dedicated commit that names the hardware session date, e.g. `chore(elrobot): record workspace measured 2026-11-22`.
- **Handoffs are shared state.** Add a dated entry to `HANDOFF.md` with your name or agent, what changed, and the next step. On merge conflicts in `HANDOFF.md` or `PROGRESS.md`, keep both sides.
- **Identity:** commit under your own git identity. Do not commit as someone else.

## On Stop
1. Update `HANDOFF.md` with: completed work, specific next steps, files changed, build status, hardware owner
2. Update `PROGRESS.md` with completed items
3. Update `GUIDELINES.md` and `PREFERENCES.md` if new conventions were established (create them if missing)
4. Run verification (tests, syntax check) before stopping
5. Confirm every change is committed (see Commit Every Change)
6. Give the 3 post-implementation suggestions and record them in `SUGGESTIONS.md` (see Post-Implementation Suggestions)

## Rules
1. Follow the plan — no unplanned features or refactors
2. Don't repeat work — check PROGRESS.md first
3. Be specific in handoffs — actionable next steps required
4. Run verification before stopping
5. Document decisions — the next agent has zero context
6. Commit each change as it finishes; never hand off with a dirty tree
7. Never move the arm without the hardware owner's typed confirmation in the session
