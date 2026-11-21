# Assistive Feeding: Safety FSM & MediaPipe Mouth-Tracking Plan

**Extends:** [docs/FEEDING_ASSISTANT_PLAN.md](FEEDING_ASSISTANT_PLAN.md) (Stage 2: Mouth Tracking, Standoff & Safe Serving)  
**Hardware:** Follower `5B61034962` (12V), Leader `5B61037051` (5V), Table Cam (`port:3-1.2.2`), Person Cam (`v4l2:2`, OBSBOT Meet SE).

---

## 1. Architecture Overview

Combines **Claude + MCP** (high-level visual reasoning, voice understanding, food/tool selection) with a **fast local safety & mouth-tracking layer** (~30 FPS on the Person Cam):

```text
[Table Cam (KD-USB)]  ──► Claude MCP (look / list_waypoints / go_to_waypoint)
                                │
                                ▼  (navigates clear -> grape_hover -> grape_pick -> clear -> serve)
[Person Cam (OBSBOT)] ──► MediaPipe FaceMesh / Lip Landmarks (MAR + EMA smoothing)
                                │
                                ▼
                     FeedingSafetyFSM + Watchdog
               (Standoff 5-10 cm -> 3-frame Mouth-Open Debounce -> Release -> Retract)
```

---

## 2. Component 1: Assistive Feeding Safety FSM (`FeedingSafetyFSM`)

Inspired by UW Personal Robotics Lab (`ada_feeding`), every facial delivery passes through a deterministic Finite State Machine in `src/feeding_vision.py`:

| State | Entry Condition | Safety Rule / Action |
| :--- | :--- | :--- |
| `IDLE` | No active feeding request | Arm rests at `clear` |
| `APPROACH` | Food grasped (`holding_object`) & face detected | Route via `clear` $\rightarrow$ `serve` |
| `HOLD_STANDOFF` | Reached `serve` (~5–10 cm from lips) | Never close the final gap; wait for user intent |
| `WAIT_MOUTH_OPEN` | Face stable at standoff | Require **3 consecutive frames** with `MAR >= 0.25` (debounce) |
| `RELEASE` | Mouth confirmed open & standoff safe | Open gripper gently to hand over bite |
| `RETRACT` | Bite delivered | Return smoothly to `clear` |
| `EMERGENCY_HOLD` | **Watchdog:** face lost $> 0.5\text{ s}$, or `mouth_width_px >= STANDOFF_MOUTH_WIDTH_PX` (too close), or voice `"stop"` | Freeze immediately (`stop()`), never release blindly |

---

## 3. Component 2: MediaPipe Lip-Landmark Tracker (`MouthStateTracker`)

Upgrades `FeedingVisionDetector.detect_mouth()` in `src/feeding_vision.py`:
1. **Lip Landmark Extraction:** Uses `mediapipe` (`FaceMesh` / `FaceLandmarker`) on the Person Cam (`OBSBOT Meet SE`) to locate inner/outer lip landmarks:
   - Upper inner lip (`13`), lower inner lip (`14`), left mouth corner (`61`), right mouth corner (`291`).
2. **Mouth Aspect Ratio (MAR):**
   $$\text{MAR} = \frac{\|\text{lip}_{13} - \text{lip}_{14}\|}{\|\text{corner}_{61} - \text{corner}_{291}\|}$$
   - `MAR >= 0.25` for **3 consecutive frames** $\Rightarrow$ `mouth_open_confirmed = True`.
3. **EMA Smoothing ($\alpha = 0.35$):** Smooths $(u, v, \text{width}, \text{MAR})$ across frames to eliminate landmark jitter.
4. **Watchdog Timer:** Tracks `last_face_seen_t`; if `now - last_face_seen_t > 0.5 s`, transitions FSM to `EMERGENCY_HOLD`.
5. **Graceful Fallback:** Falls back cleanly to OpenCV Haar cascade if MediaPipe is unavailable on a CPU-only teammate laptop.

---

## 4. Implementation & Test Checklist

- [x] **Step 1:** Install `mediapipe` in `.venv` and verify live lip landmarks on Person Cam (`OBSBOT`).
- [x] **Step 2:** Implement `MouthStateTracker` (MediaPipe + MAR + EMA + 3-frame debounce + watchdog) and `FeedingSafetyFSM` in `src/feeding_vision.py`.
- [x] **Step 3:** Surface live `MAR`, `mouth_open_confirmed`, and `FSM state` in Mission Control (`src/digital_twin_server.py` -> `http://localhost:8080`).
- [x] **Step 4:** Add unit tests in `tests/test_pipeline.py` covering MAR calculation, 3-frame debounce, face-loss watchdog, and FSM transitions.
- [ ] **Step 5 (Bench Test):** Start `./cli.sh reset && ./cli.sh start`, sit in front of OBSBOT Person Cam, verify `OPEN` / `CLOSED` mouth & standoff live on `http://localhost:8080`.
- [ ] **Step 6 (Live Demo):** Teach `grape_pick` & `serve` waypoints, verify gripper direction, run Claude MCP dry-run (`ELROBOT_ALLOW_MOTION=0`) $\rightarrow$ live run (`ELROBOT_ALLOW_MOTION=1`).
