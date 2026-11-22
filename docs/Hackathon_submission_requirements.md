## **Competition Rules & Submission Guidelines**

To compete in the hackathon and have your project considered by the jury of your track, all participants must adhere to the following rules and submission requirements. Failure to meet these guidelines may result in disqualification.

All submissions must be completed **before Sunday, November 22 at 16:30** through the submission form: https://tally.so/r/GexoxQ

**Every team must submit three things:**

1. **A video** (3 minutes videos showcasing your project)

2. **A GitHub repository** with the project code and relevant technical documentation

3. **A short presentation** (slides) to present the project to the audience in case your team wins its track.

**Simulation and Software track — video requirements**

**What to submit** 

1. **A clear 3 minute pitch**

2. **An explanation of your solution**

3. **A demo or screenshots of how your solution works**

We strongly recommend that the video includes at least one team member speaking to camera. It is also important to show the actual solution, prototype, demo, or screenshots.

**Robotics Tracks – Video Requirements**

Each team must submit a 3**-minute showcase video** showing the robot in action and explaining the idea behind the project.

**Accepted video formats**

- YouTube link, preferably unlisted
- Google Drive link

Please make sure the link is accessible and does not require special permissions.

**GitHub repository** 

Please make sure the repository is public or accessible to the judging team.

**Presentation**

Every team prepares a **short presentation** of their project. If your team wins its track, you will use it to present your project live on the main stage to the jury and the audience (5 minutes).

---

## **Ready-to-Submit Form Inputs (`https://tally.so/r/GexoxQ`)**

Copy and paste each field below directly into the **2nd edition Berlin Robotics & AI hackathon Submission** Tally form once all files are uploaded before **Sunday, November 22 at 16:30**.

### 1. Email *(Required)*
```text
elmusleh.mohammad@gmail.com
```

### 2. Team Name + team number *(Required)*
> *Status: Team number is confirmed (**Team 6**). Pick a final team name below before submitting.*

```text
Team 6 — CareArm
```
*(Alternative name ideas if you prefer another: `Team 6 — NormaFeed`, `Team 6 — BiteBot`, `Team 6 — MealMate`, `Team 6 — OpenBite`)*

### 3. All team members (Name + Email) *(Required)*
```text
Jan Schulz (jan.schulz@cileria.com)
Jafer Sharfeddin (j.sharfeddin@gmail.com)
Mohammad El-Musleh (elmusleh.mohammad@gmail.com)
```

### 4. What are you building? *(Required)*
```text
We built an Assistive Feeding Robot on the 7+1 DOF NormaCore ElRobot arm to restore mealtime independence for people with upper-limb mobility impairments.

A user simply speaks what they want to eat (e.g., "Give me a grape" or "I'd like chocolate") through our hands-free, bilingual (EN/DE) Web Console powered by OpenAI gpt-transcribe and spoken TTS/audio chimes. Our architecture strictly separates semantic reasoning from real-time safety ("Claude decides, local code acts fast"):

- Semantic Brain (Claude + 15-Tool MCP Server): Inspects the overhead Table Camera, selects the right recorded trajectory/food zone, and orchestrates recovery—protected by 3-layer scope guardrails (<1 ms pre-LLM prompt-injection/off-topic gatekeeper, XML transcript isolation, and whitelisted MCP schemas) with a live Developer Action Trace.
- 3-Camera Closed-Loop Vision (~30 FPS): Combines an overhead Table Camera (food/bowl detection), a wrist-mounted Gripper Camera (<5 ms LAB jaw-zone ROI grasp verification + bounded ±2% base alignment), and an OBSBOT face camera running MediaPipe Face Landmarker.
- Human-First Face Safety: The arm never closes the last 5–10 cm gap to the face. It pauses at a safe standoff, speaks a readiness cue, and waits for a per-user calibrated Mouth-Open confirmation (MAR + 3-frame debounce + 0.6 s face-loss watchdog). Saying "Stop!" or pressing Emergency Stop bypasses the LLM entirely and holds all 8 ST3215 servos in <0.5 s without dropping the arm, backed by calibrated joint clamps, overload current protection, and a physical 12 V cutoff.
```

### 5. Demo Video Link *(Required — open & shared Google Drive folder)*
```text
https://drive.google.com/drive/folders/1Q5BmuXYwDzb8l9mM50GJKotJGi_aoseH?usp=sharing
```
*(Reminder: upload the 3-minute showcase video into this folder before submitting.)*

### 6. Presentation Link *(Required)*
```text
https://docs.google.com/presentation/d/1K_Qs0a0WqHv027SaB6GGvUq6lRjIOtOPxUlSuUZVYMk/edit?usp=sharing
```
*(Reminder: import/sync `docs/Assistive_Feeding_Robot_Pitch.pptx` into this Google Slides link and confirm "Anyone with the link can view".)*

### 7. GitHub Repository Link *(Required — must be public)*
```text
https://github.com/elmusleh/normacore-hackathon-2026
```

### 8. Which track are you competing in? *(Required)*
- [x] **Normacore**
- [ ] Prior labs
- [ ] Hugging face
- [ ] Almedia
- [ ] Dream labs
- [ ] Durance AI

### 9. Terms & Conditions *(Required)*
- [x] **I agree** *(Event Terms: https://app.notion.com/p/Hacklab-Event-Terms-Conditions-37b6641d682f80dabc33eff601c28c3d)*

---

## **Pre-Submission Checklist (Deadline: Sunday, Nov 22 — 16:30)**
- [ ] Confirm final team name for **Team 6** (update Field #2 above if changed)
- [ ] Upload 3-minute demo video to the [shared Google Drive folder](https://drive.google.com/drive/folders/1Q5BmuXYwDzb8l9mM50GJKotJGi_aoseH?usp=sharing) and verify public "Viewer" access in an incognito tab
- [ ] Upload/finalize slides in [Google Slides](https://docs.google.com/presentation/d/1K_Qs0a0WqHv027SaB6GGvUq6lRjIOtOPxUlSuUZVYMk/edit?usp=sharing) and verify public "Viewer" access in an incognito tab
- [ ] Push final code and confirm `https://github.com/elmusleh/normacore-hackathon-2026` is **Public**
- [ ] Open `https://tally.so/r/GexoxQ`, paste Fields #1–#7, check **Normacore** and **I agree**, and click **Register**
