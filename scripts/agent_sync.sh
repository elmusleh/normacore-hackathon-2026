#!/usr/bin/env bash
# ==============================================================================
# agent_sync.sh - Fetch and fast-forward before an agent starts implementing.
#
# Safe by design: it never stashes, resets, rebases or force-pulls. It only
# fast-forwards when the working tree is clean and the branch is behind its
# upstream. Anything else is reported and left for a person to decide.
#
# Exit codes:
#   0  in sync (or ahead only, nothing to pull)
#   1  could not reach the remote (offline); local status is still shown
#   2  uncommitted changes present; pull skipped
#   3  diverged, detached HEAD, or fast-forward refused; a person must decide
#   4  branch has no upstream; nothing to pull
# ==============================================================================
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1

BRANCH=$(git branch --show-current)
if [ -z "$BRANCH" ]; then
    echo "SYNC: detached HEAD. Check out a branch before starting work."
    exit 3
fi

echo "== Fetch =="
if ! timeout 60 git fetch --prune origin; then
    echo "SYNC: could not reach origin (offline or no access). Local state shown below; nothing was pulled."
    RC=1
else
    RC=0
fi

UPSTREAM=$(git rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>/dev/null || true)
echo "branch: $BRANCH   upstream: ${UPSTREAM:-none}"

DIRTY=$(git status --porcelain --untracked-files=no)
if [ -n "$DIRTY" ]; then
    echo "== Uncommitted changes (someone's work in progress is not pulled over) =="
    echo "$DIRTY"
fi

# Changes on origin/main since this branch split from it. Check these before editing.
if git rev-parse --verify --quiet origin/main >/dev/null; then
    BASE=$(git merge-base HEAD origin/main 2>/dev/null || true)
    if [ -n "$BASE" ]; then
        MAIN_NEW=$(git log --oneline "$BASE..origin/main" | head -20)
        if [ -n "$MAIN_NEW" ]; then
            echo "== Commits on origin/main since your branch split (check these files before editing) =="
            echo "$MAIN_NEW"
            echo "-- files --"
            git diff --name-only "$BASE" origin/main | head -40
        fi
    fi
fi

if [ -z "$UPSTREAM" ]; then
    echo "SYNC: '$BRANCH' has no upstream, so there is nothing to pull. Push it with -u when asked."
    exit 4
fi

AHEAD=$(git rev-list --count "@{u}..HEAD")
BEHIND=$(git rev-list --count "HEAD..@{u}")
echo "ahead: $AHEAD   behind: $BEHIND"

if [ "$BEHIND" -eq 0 ]; then
    echo "SYNC: up to date with $UPSTREAM."
    exit "$RC"
fi

if [ "$AHEAD" -gt 0 ]; then
    echo "SYNC: diverged (your commits and upstream commits both exist). Not touched. Rebase per AGENTS.md Team Workflow, or ask the owner."
    exit 3
fi

if [ -n "$DIRTY" ]; then
    echo "SYNC: behind by $BEHIND, but uncommitted changes are present. Pull skipped. Commit or ask the owner about them, then run sync again."
    exit 2
fi

if git merge --ff-only "@{u}" >/dev/null 2>&1; then
    echo "SYNC: fast-forwarded $BEHIND commit(s) from $UPSTREAM."
    exit "$RC"
fi

echo "SYNC: fast-forward refused. Not touched. Ask the owner."
exit 3
