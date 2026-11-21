### Post-Implementation Suggestions

1. Calibrate tabletop homography with printed AprilTags — Priority 95% (Critical) [Best practices]
   What: Place the printed 4-corner AprilTags on the workspace table under `/dev/video2` or `/dev/video4` and run `python3 scripts/calibrate_camera.py`.
   Why: Transforms 2D image coordinates into exact millimeter $(X, Y)$ coordinates relative to the arm base, allowing autonomous agents to see objects on the table without coordinate hallucinations.
   How: Print `docs/apriltags_printable.html` or display on a smartphone, place at table corners, and execute `python3 scripts/calibrate_camera.py`.
   Status: ⏳ Unimplemented
   Reason Deferred: Requires physical placement of tags on the hackathon desk.

2. Teach initial core waypoints (`home`, `hover`, `bin`) — Priority 85% (High value) [Best practices]
   What: Use the leader arm or `./cli.sh hw teach <name>` to record default reference positions into `config/waypoints.json`.
   Why: Provides deterministic, collision-safe poses that the autonomous agent can return to between pick and place operations.
   How: Move the arm to desired rest and clearance positions and run `./cli.sh hw teach home` and `./cli.sh hw teach clear`.
   Status: ⏳ Unimplemented
   Reason Deferred: To be performed on the physical table alongside the team.

3. Add dynamic role indicators to web console / CLI HUD — Priority 72% (Nice to have) [Professionalism]
   What: Display a visual banner or terminal HUD clearly indicating Master (`5B61034962`) and Slave (`5B61037051`) with live joint angle comparison.
   Why: Prevents confusion between identical-looking leader and follower buses during rapid demo presentations and judging rounds.
   How: Add a small status banner in `scripts/teleop_sync.py` and the digital twin dashboard.
   Status: ⏳ Unimplemented
   Reason Deferred: Core sync functionality is verified; UI embellishment can be added before Sunday pitch.
   What: Run `pip install -r requirements.txt` and execute `pytest tests/test_pipeline.py` on your machine.
   Why: Ensures your Python environment (especially NumPy and OpenCV/Pillow) is 100% verified and all 5 unit/integration tests pass before traveling.
   How: Run `pip install -r requirements.txt && pytest tests/test_pipeline.py -v`.
   Status: ⏳ Unimplemented
   Reason Deferred: Verification step for user's terminal environment before traveling.

2. Verify `.mcp.json` tool discovery in Claude Code or Cursor — Priority 88% (High value) [Best practices]
   What: Open this repository in Claude Code or Cursor and confirm that the `normacore-robot` MCP server is detected and tools are available.
   Why: Auto-registering tools means your AI agent can call `get_calibrated_view`, `pick_at`, and `verify_grasp` directly without manual command-line flags.
   How: Run `claude mcp list` or inspect Cursor Settings -> MCP Servers.
   Status: ⏳ Unimplemented
   Reason Deferred: Requires testing within user's specific editor/agent UI.

3. Pack essential hardware accessories: USB-A/C adapters, powered hub, and masking tape — Priority 82% (High value) [Professionalism]
   What: Put a USB-C to USB-A adapter, a 2m USB extension cable, and a small roll of masking tape into your hackathon backpack.
   Why: In live robotics hackathons, desk outlets and laptop port arrangements are unpredictable. Masking tape is invaluable for taping down AprilTags and marking bin boundaries.
   How: Pack these physical items in your travel bag tonight.
   Status: ⏳ Unimplemented
   Reason Deferred: Physical packing task before departure for Berlin.

4. Pre-download Python wheels and Protobuf packages offline — Priority 78% (High value) [Reliability]
   What: Download cached pip wheels for your environment (`pip download -r requirements.txt -d ./pip_cache`) so you can reinstall without internet.
   Why: If venue internet drops or restricts PyPI access on Saturday, you can install any missing package locally from cache.
   How: Run `pip download -r requirements.txt -d ./pip_cache`.
   Status: ⏳ Unimplemented
   Reason Deferred: Preventive measure to run before leaving home Wi-Fi.

5. Bookmark NormaCore Station Web console default URL and offline docs — Priority 70% (Nice to have) [Professionalism]
   What: Bookmark `http://localhost:8889` (the Station web console default, per `docs/NormaCore_Repositories_and_Tooling.md`) and save the Station README as an offline PDF.
   Why: Gives you instant access to manual motor calibration controls and joint sliders during the first 30 minutes of hardware bring-up.
   How: Save the Station docs locally in `docs/`.
   Status: ⏳ Unimplemented
   Reason Deferred: Optional convenience step ahead of kickoff.

6. Verify the URDF-to-motor mapping before any Cartesian move — Priority 92% (Critical) [Best practices]
   What: Confirm which ST3215 motor ID drives which URDF joint (`rev_motor_01` to `rev_motor_08`) and in which direction, using the Station web console on the real arm.
   Why: Cartesian tools (`pick_at`, `place_at`) need correct joint kinematics. A wrong mapping would move the arm in the wrong direction on the first try.
   How: With the arm on the table, jog one motor at a time at slow speed from the Station console, note the direction, and write the table into `docs/elrobot_hardware_bridge.md`.
   Status: ⏳ Partly done (tool exists, arm check pending)
   Reason Deferred: `./cli.sh hw identify` now records the mapping, but the result still needs checking on the physical arm.

7. Measure the table and set workspace limits — Priority 60% (Nice to have) [Professionalism]
   What: Measure the real table, then set the limits in `config/elrobot.json`. The limits are now read from one file (the old hardcoded values are gone).
   Why: Mismatched limits can make the agent plan targets the real arm cannot reach, or reject ones it can.
   How: Follow "Step 11" in `docs/elrobot_hardware_bridge.md`, then run `./cli.sh hw workspace`.
   Status: ⏳ Unimplemented
   Reason Deferred: Needs a tape measure on site. Config and tooling are in place.

8. Run the test suite on every push with a CI workflow — Priority 50% (Nice to have) [Best practices]
    What: A small GitHub Actions job that installs `requirements.txt` and runs `pytest` on each push.
    Why: Catches broken safety helpers before they reach the lab laptop on Saturday.
    How: Add `.github/workflows/tests.yml` with checkout, Python 3.11 setup, `pip install -r requirements.txt`, and `pytest tests/`.
    Status: ⏳ Unimplemented
    Reason Deferred: Repo has no remote set up for hackathon work yet, and the job would also need the NormaCore SDK checkout.

9. Rotate and prune old run logs — Priority 40% (Optional) [Professionalism]
    What: Delete hardware logs older than a set number of days, so `logs/` does not grow forever.
    Why: Every run writes a new file, and at DEBUG level each file can be several KB. This matters only over many sessions.
    How: In `src/elrobot_log.py`, keep the newest 50 files per tool name and delete the rest when a new run starts.
    Status: ⏳ Unimplemented
    Reason Deferred: Low value for hardware day; logs are small and the bundle command only reads the most recent files.

10. Measure the workspace using the arm's own taught poses — Priority 75% (High value) [Best practices]
    What: Teach the arm to each table corner and read the joint positions, instead of relying only on a tape measure.
    Why: Joint readings at the corners show the arm's reach directly, so the workspace limits match what the arm can actually do.
    How: With torque off, move the gripper to each corner and run `./cli.sh hw teach corner_1` through `corner_4`. Then compare the taught poses with the measured limits in `config/elrobot.json`.
    Status: ⏳ Unimplemented
    Reason Deferred: Needs the physical arm, and the tape measure check (item 9) is the simpler first step.

11. Record and replay named sequences — Priority 55% (Nice to have) [Best practices]
    What: Chain several waypoints into one named routine, such as "pick then place", and run it with one command.
    Why: The sorting demo will repeat the same route many times. One command is less error-prone than typing each goto.
    How: Store a list of waypoint names under `config/sequences.json`, and add `./cli.sh hw run-seq <name>` that calls goto for each step and stops on the first failure.
    Status: ⏳ Unimplemented
    Reason Deferred: Build it after single gotos work on the arm.

12. Handle encoder wrap-around in the overload detector — Priority 45% (Optional) [Best practices]
    What: The overload check compares motor positions, so it can misread movement when a joint crosses the encoder's zero point (0 and 4095).
    Why: Crossing zero is rare in the current workspace, but a missed stall there could strain a motor.
    How: In `OverloadDetector.update`, measure movement as the shorter distance around the 0–4095 circle.
    Status: ⏳ Unimplemented
    Reason Deferred: No joint crosses zero in the planned workspace. Fix it if a range changes.

13. Enforce the commit checklist with a git pre-commit hook — Priority 74% (High value) [Best practices]
    What: A script that runs automatically before each commit, checks that the tests pass and that `CHANGELOG.md` is staged, and blocks the commit if not.
    Why: Right now the commit rules only live in `AGENTS.md`. A hook catches a forgotten test run or changelog entry before it reaches the shared history.
    How: Create `.githooks/pre-commit` with a few lines that run `python3 -m pytest tests/ -q` and check `git diff --cached --name-only` for `CHANGELOG.md`, then run `git config core.hooksPath .githooks` once on each machine.
    Status: ⏳ Unimplemented
    Reason Deferred: Adds a gate to every commit for the whole team. Needs agreement on which checks are mandatory before it is turned on.

14. Add a hardware-safety checklist to pull requests that touch motion code — Priority 86% (High value) [Security]
    What: A short checklist that every pull request changing motion code must complete before it is merged, covering torque state, workspace clearance, and a test run on the bench.
    Why: The arm can hit people or the table. A code change that looks correct on paper can still move the arm the wrong way, and a reviewer who is not at the bench cannot see that.
    How: Add `.github/pull_request_template.md` with checkboxes: "tests pass", "no `hw jog`/`hw goto` run without the hardware owner", "workspace clear", "E-stop (`./cli.sh hw stop`) tested".
    Status: ⏳ Unimplemented
    Reason Deferred: Needs the team to agree who the hardware owner is and what counts as a bench test before the checklist can be written.

15. Use a lock file so only one terminal can send motion commands — Priority 78% (High value) [Security]
    What: A small lock file that the motion commands check before moving the arm, so a second terminal cannot start a move while the first one is running.
    Why: Two people or two agents sending commands at the same time can fight each other on the same motors. A lock stops that before any motor moves.
    How: In `scripts/hw_day.py`, create `data/hw_motion.lock` with the process ID when a move starts, refuse new moves while the lock exists and the process is alive, and remove the lock when the move ends.
    Status: ⏳ Unimplemented
    Reason Deferred: Changes the motion code, which needs the real arm to test properly. Should wait until the first bench session confirms the current flow.

16. Save each camera's stable port path in the config — Priority 72% (High value) [Best practices]
    What: Record which USB port each camera is plugged into (for example, "overhead" and "wrist") in `config/`, so the software finds the right camera without guessing.
    Why: Camera numbers like `/dev/video2` change after a replug. Two of our cameras share the same name, so a wrong guess could send the wrong image to the robot's logic.
    How: Use `ls -l /dev/v4l/by-path/` to find each camera's path, confirm it with a test frame, and add the paths to `config/elrobot.json` in a calibration commit.
    Status: ⏳ Unimplemented
    Reason Deferred: Needs the cameras plugged into their final ports and a confirmed overhead/wrist assignment from the hardware owner first.

17. Add a one-command bench readiness check — Priority 65% (Nice to have) [Best practices]
    What: A single command that checks serial permissions, the Station, the bus serial numbers and the cameras, and prints pass or fail for each.
    Why: Right now setup problems are found one at a time during a bench session. One check before powering the arm saves time and avoids the permission and bus-selection mistakes we have already hit.
    How: Add a `./cli.sh bench-check` subcommand that reuses the existing preflight checks and adds a serial permission check and a camera frame check. It should only read, never move the arm.
    Status: ⏳ Unimplemented
    Reason Deferred: Mostly a convenience. The manual steps in `docs/team_setup.md` cover it until the team has used them on a bench session.

18. Check that every link in the docs points to a real file — Priority 45% (Nice to have) [Professionalism]
    What: An automatic check that flags any broken link or missing file path in the Markdown docs.
    Why: The team docs now link to each other. A renamed file would leave a broken link that a new team member finds only when they are stuck.
    How: Add a small test in `tests/` that reads each `docs/*.md` and `AGENTS.md`, extracts relative links, and fails if a target file does not exist.
    Status: ⏳ Unimplemented
    Reason Deferred: Useful but not urgent. The docs are new and few, so a manual check is enough for now.

19. Add automated tests for the sync script's four outcomes — Priority 76% (High value) [Best practices]
    What: Automatic tests that prove `scripts/agent_sync.sh` behaves correctly when it is behind, dirty, diverged or offline.
    Why: The sync script decides whether a teammate's work gets pulled over an agent's edits. Its fast-forward, dirty-tree and diverged paths were not run in a real test yet, so a bug there could cause the very conflicts it is meant to prevent.
    How: Add `tests/test_agent_sync.py` that builds a throwaway bare remote and two clones in a temporary folder, makes a commit in one clone, and runs the script in the other for each case. Check the exit code in each case.
    Status: ⏳ Unimplemented
    Reason Deferred: Writing the test is not hard, but the first run was blocked. Scratch-repo tests need a go-ahead, so this stays on the list until it is approved.

20. Run the sync check automatically when an agent session starts — Priority 68% (High value) [Best practices]
    What: A session-start hook that runs `./cli.sh sync` as soon as an AI agent session opens, so the agent does not depend on remembering to do it.
    Why: The rule in `AGENTS.md` only works if every agent follows it. A hook makes the sync happen every time and shows the result before any edit.
    How: Add a `SessionStart` hook in the project's `.claude/settings.json` that runs `./cli.sh sync` and prints the output. Test it once on a clean branch.
    Status: ⏳ Unimplemented
    Reason Deferred: Changes the agent tool configuration for everyone on the team. Needs a team decision first.

21. Flag stale feature branches in continuous integration — Priority 50% (Nice to have) [Best practices]
    What: An automatic check on each pull request that warns when the branch is far behind `main`.
    Why: A long-stale branch is the main source of painful merge conflicts. An early warning gives the author time to rebase while the changes are still small.
    How: Add a GitHub Actions workflow that runs `git rev-list --count HEAD..origin/main` on each pull request and posts a warning comment when the count is above a set limit, such as 20.
    Status: ⏳ Unimplemented
    Reason Deferred: Needs the repository to use GitHub Actions and pull requests. Nice to have once the team is using pull requests regularly.

23. Record the Station binary's checksum next to the SDK's — Priority 55% (Nice to have) [Security]
    What: Store the SHA-256 of `bin/station` in the check script, so `sdk-check` also proves the binary is the one the team agreed on.
    Why: The check currently confirms the version string the binary prints. A replaced binary that prints the same version would pass. A checksum closes that gap.
    How: Run `sha256sum bin/station` on a known-good machine, add the value as a constant in `scripts/sdk_check.py`, and add a check that compares it.
    Status: ⏳ Unimplemented
    Reason Deferred: Only useful once the team's Station binary is fixed and shared. Doing it now would lock in a binary that may still change.

24. Require an approval note when the SDK pin changes — Priority 50% (Nice to have) [Professionalism]
    What: A pull request check that flags any change to `.gitmodules` or the submodule's commit, and asks for the owner's approval in the description.
    Why: The SDK pin decides which NormaCore code every teammate runs. A pin changed by accident would spread to the whole team without anyone noticing in review.
    How: Add a GitHub Actions workflow that runs `git diff --name-only origin/main...HEAD` and fails the check if `.gitmodules` or `external/norma-core` appears without the words "SDK pin approved" in the pull request body.
    Status: ⏳ Unimplemented
    Reason Deferred: Needs GitHub Actions and pull requests in regular use. The team has not used pull requests yet.

25. Keep an offline mirror of the pinned SDK — Priority 58% (Nice to have) [Best practices]
    What: A copy of the SDK at commit `5f4f805` on a team drive or in a backup, so a bench session can go ahead even if GitHub is unreachable.
    Why: The Station venue may have poor internet. Without a mirror, a new machine cannot fetch the submodule on the day.
    How: Run `git bundle create norma-core-5f4f805.bundle 5f4f805` in the submodule folder, store the bundle with its SHA-256 on the team drive, and add the restore steps to `docs/team_setup.md`.
    Status: ⏳ Unimplemented
    Reason Deferred: Only needed if the team will work offline. The owner should decide whether a mirror is needed for the venue.

26. Remove the old SDK backup once every machine uses the submodule — Priority 35% (Optional) [Professionalism]
    What: Delete the leftover copies `external/norma-core-snapshot/` and `external/norma-core-main.tar.gz`, which the submodule has replaced.
    Why: Two unused copies of the SDK take up space and can be mistaken for the real one. Removing them stops a teammate from using the wrong copy.
    How: After every machine has run `./cli.sh sdk-check` and passed, delete both paths. They are gitignored, so nothing is committed.
    Status: ⏳ Unimplemented
    Reason Deferred: Deleting files needs the owner's go-ahead, and the backups are the fallback if the submodule has a problem on the bench.
