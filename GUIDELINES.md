# Project Guidelines: NormaCore Physical AI & Tabletop Robotics

Standards, conventions, and safety rules for all code and AI agents working in this repository.

---

## 1. General Rules
- Match existing code patterns and modular separation (`src/` for logic, `tests/` for verification, `docs/` for deep specs).
- Run the full verification suite (`python3 -m pytest tests/test_pipeline.py`) before finishing any turn or commit.
- Never commit with broken tests. Stage explicit paths (`git add <path> ...`), never `git add -A`.
- Update `CHANGELOG.md` before every commit following Conventional Commits.

---

## 2. Robotics & Safety Conventions
- **The Cartesian Boundary Rule:** Agents must NEVER command raw joint angles to the 7+1 DOF arm. Always use high-level Cartesian coordinates $(X, Y, Z)$ in millimeters relative to the arm base origin $(0, 0)$.
- **Strict Table Floor Limit ($Z$-Clamp):** The table surface is at $Z \approx 0\text{mm}$. The safety layer must strictly enforce $Z \ge 12.0\text{mm}$ (table floor clamp) at all times to prevent slamming the gripper into the desk or damaging the ST3215 servos.
- **Safe Clearance Heights:**
  - `Z_TRANSIT_HEIGHT = 70.0mm`: All horizontal moves between tabletop zones must occur at or above this clearance to avoid knocking over other objects.
  - `Z_HOVER_HEIGHT = 45.0mm`: Pre-grasp descent approach.
  - `Z_GRASP_HEIGHT = 14.0mm`: Grasping level.
- **Workspace Bounds:**
  - $X \in [-180.0, 180.0]\text{ mm}$ (Left is negative, Right is positive).
  - $Y \in [90.0, 270.0]\text{ mm}$ (Forward into workspace from arm base).

---

## 3. Vision & Coordinate Calibration
- Always calibrate camera space to physical tabletop space using 4-corner fiducial markers (AprilTags / ArUco IDs 0–3).
- Use `TabletopCalibrator` from `src/vision_homography.py` to project the metric coordinate grid onto the camera feed.
- Do not pass uncalibrated 2D pixel coordinates to LLMs. Always provide metric annotations.

---

## 4. Closed-Loop Recovery Architecture
- Every physical manipulation task must follow the **Perceive $\to$ Act $\to$ Verify** cycle:
  1. Capture scene view (`get_calibrated_view()`).
  2. Plan and execute pick (`pick_at(x, y)`).
  3. Verify grasp before placing (`verify_grasp()`).
  4. If grasp failed (`EMPTY_GRIP`), trigger autonomous recovery: re-capture scene, update coordinates, re-attempt.

---

## 5. Linux Permissions & Hardware Communication
- Never run robot scripts with `sudo`.
- Configure Linux serial permissions via group membership (`dialout`) and udev rules using `scripts/setup_usb_serial.sh`.
