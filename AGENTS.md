# AI Agent Instructions

This project uses `.ai-sync/` for cross-platform AI agent synchronization.

## On Start
1. **Sync before you implement:** run `./cli.sh sync`. It fetches from origin and fast-forwards only when your tree is clean and the branch is behind. It never stashes, resets or force-pulls. Act on the exit code:
   - `0`: in sync. Continue.
   - `1`: offline. Continue on local code, and say so in your final message.
   - `2`: uncommitted changes exist, so the pull was skipped. Do not edit files that are being changed upstream. Ask the owner before you pull.
   - `3`: diverged, detached, or fast-forward refused. Stop and ask. Do not rebase on your own.
   - `4`: no upstream. Nothing to pull. Continue.
   It also brings the NormaCore submodule to its pinned commit.
   The output also lists commits on `origin/main` since your branch split, with their files. Check those files before you edit them.
2. Note any modified files you did not touch; they belong to someone else.
3. Read `.ai-sync/HANDOFF.md` — current state, what was done, what's next, who owns the hardware
4. Read `.ai-sync/PROGRESS.md` — completed vs pending tasks
5. Read `docs/FEEDING_ASSISTANT_PLAN.md` — the current team plan, safety rules and task list (do not deviate)
6. Read `.ai-sync/PLAN.md` only for history

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
- Never commit `data/`, `logs/`, `station_data/`, `bin/`, other contents of `external/` (all gitignored) or secrets. Never commit edits made inside the `external/norma-core` submodule.
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
- **Handoffs are shared state.** Add a dated entry to `HANDOFF.md` with your name or agent, what changed, and the next step. Put the newest entry at the top. Append to shared files and never rewrite someone else's entry. On merge conflicts in `HANDOFF.md`, `PROGRESS.md` or `CHANGELOG.md`, keep both sides.
- **SDK pin:** `external/norma-core` is a submodule pinned to `5f4f805`. Change the pin only in its own commit, `chore(sdk): pin norma-core to <commit>`, after the owner approves it and `./cli.sh sdk-check` passes. Teammates then run `./cli.sh sync`, which updates the submodule.
- **Identity:** commit under your own git identity. Do not commit as someone else.

## Setup and Safety (read these first)
- **New machine:** follow `docs/team_setup.md` before the first run.
- **Before any motion command** (`hw jog`, `hw goto`, `hw torque on`, `hw identify`, `hw probe-current`): read `docs/bench_safety.md`. Stop means `./cli.sh hw stop`, and the 12 V switch is the real stop.
- **Never guess a physical fact** (which serial port is which arm, which camera is overhead). Ask the hardware owner, or confirm with a read-only check.

## Where Things Live
- `src/`: logic, Station client, MCP server, vision, kinematics and safety.
- `scripts/`: command-line tools (`hw_day.py`, `hardware_preflight.py`, `setup_usb_serial.sh`).
- `config/`: committed calibration and workspace limits. Change these only in calibration commits.
- `tests/`: offline tests. They need no hardware.
- `docs/`: runbooks and setup guides. Start with `docs/team_setup.md`, `docs/bench_safety.md` and `docs/elrobot_hardware_bridge.md`.
- `external/norma-core/`: the NormaCore SDK, a git submodule pinned to commit `5f4f805` (see `.gitmodules`). Do not edit files inside it.
- `data/`, `logs/`, `station_data/`, `bin/`, and other `external/` contents (for example `external/lerobot_robot_elrobot/`): local only, gitignored.
- Where to write what (one owner per fact):
  - `GUIDELINES.md` and `PREFERENCES.md`: rules and conventions.
  - `FINDINGS.md`: observed facts, each with its evidence and status.
  - `SUGGESTIONS.md`: open ideas and next steps.
  - `.ai-sync/HANDOFF.md`: what is happening now, and who has the hardware.
- Team roles: the split in `README.md`.

## Definition of Done
A change is finished when all of these are true:
- Tests pass (`python3 -m pytest tests/`).
- `CHANGELOG.md` has an entry.
- It is committed on a branch, with a clean `git status` for your files.
- A pull request is open, or the branch is named in `HANDOFF.md`.
- `HANDOFF.md` says what changed and what comes next.
- For motion code: the bench checklist in `docs/bench_safety.md` was followed, or it is marked "not tested on the arm" in `HANDOFF.md`.

## Testing
- **Offline (anywhere):** `python3 -m pytest tests/`. No hardware, no Station.
- **Bench (needs the arm and the hardware owner):** `./cli.sh preflight --bus <serial>` and `./cli.sh hw motors`, both read-only.
- Do not add a test that moves a motor to the default suite. Hardware tests must be separate and clearly marked.

## Conventions
- Follow `GUIDELINES.md` and `PREFERENCES.md`. They are the owners of the coding and safety rules. Do not copy them here.
- Python 3.10+. Match the style of the file you are editing.
- Conventional Commits for every commit message.

## Asking, Reporting and Blockers
- When a request is ambiguous, say which reading you took and why. Ask first only before changing hardware config or motion code.
- Write blockers in `HANDOFF.md` under Blockers, with the exact error and the log path, and say so in your final message.
- Do not hide a partial result. Report what passed, what failed, and what was not run.

## Privacy and Secrets
- Camera frames and logs can show people and their names. Keep them out of git and out of shared chats. Review `./cli.sh hw bundle` output before sharing it.
- No keys or tokens in the repo. `.env` files stay local.
- Do not send repo contents to an outside service unless the owner has agreed to it.

## On Stop
1. Update `HANDOFF.md` with: completed work, specific next steps, files changed, build status, hardware owner
2. Update `PROGRESS.md` with completed items
3. Update `GUIDELINES.md` and `PREFERENCES.md` if new conventions were established (create them if missing). Record each verified hardware or setup observation in `FINDINGS.md` with its evidence.
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
