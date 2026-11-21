# Feeding Assistant: Diagrams

Visual companion to [FEEDING_ASSISTANT_PLAN.md](FEEDING_ASSISTANT_PLAN.md). GitHub and VS Code
(with a Mermaid preview extension) draw these as pictures. Boxes marked *planned* do not exist yet.

## 1. System model: who talks to whom

```mermaid
flowchart LR
    person(["Person<br/>(cannot use arms)"])

    subgraph LAPTOP["Main laptop"]
        direction TB
        subgraph VOICE["Voice — D (planned)"]
            stt["Speech-to-text<br/>src/voice.py"]
            tts["Text-to-speech<br/>say()"]
            vstop["Voice stop listener<br/>scripts/voice_stop.py"]
        end

        claude{{"Claude<br/>meal-assistant session<br/>(decides what and when) — B"}}

        subgraph MCP["MCP server src/robot_mcp_server.py"]
            tools["RobotTools<br/>src/robot_tools.py<br/>safety limits, waypoints,<br/>gripper, look"]
            mouth["Mouth tracker — C (planned)<br/>src/mouth_tracker.py<br/>MediaPipe ~30 FPS"]
        end

        hw["Hardware bridge<br/>src/elrobot_hardware.py<br/>clamps, torque checks,<br/>overload guard, hold"]
        cfg[("config/elrobot.json<br/>config/waypoints.json<br/>foods, zones, poses")]
        station["NormaCore Station<br/>bin/station<br/>TCP 8888 · web 8889"]
    end

    subgraph HW["Hardware — A"]
        arm["ElRobot follower<br/>8 × ST3215 servos"]
        tcam["Table camera<br/>USB 3-2.4"]
        gcam["Gripper camera<br/>USB 3-2.2"]
        mic["Microphone"]
    end

    person -- "I want rice" --> mic
    mic --> stt --> claude
    mic --> vstop
    claude -- "tool calls" --> tools
    claude -- "find_mouth / serve_to_mouth" --> mouth
    tools --> hw
    mouth --> hw
    tools -. reads .-> cfg
    hw <--> station
    vstop -- "STOP: hold all motors<br/>(bypasses Claude)" --> hw
    station <--> arm
    tcam --> station
    gcam --> station
    claude --> tts --> person
    arm -- "food at standoff" --> person
```

**Read it as:** the person speaks → Claude decides → tools move the arm through the safety layers →
the Station drives the servos and records the cameras. Two paths skip Claude on purpose: the **voice stop**
(must be instant) and the **mouth approach loop** (must be fast).

## 2. Layers: what is allowed to move the arm

```mermaid
flowchart TB
    L1["Claude — chooses food, tool, next step<br/>slow: seconds per decision"]
    L2["MCP tools — named actions only<br/>go_to_waypoint, set_gripper, nudge ≤ 5%, serve_to_mouth"]
    L3["RobotTools — motion switch, route via 'clear',<br/>max move size, speed cap"]
    L4["Hardware bridge — calibrated range clamp,<br/>torque/fault checks, overload hold"]
    L5["Station → servos"]
    STOP["Voice stop / stop() / power plug"]

    L1 --> L2 --> L3 --> L4 --> L5
    STOP -. "hold, any time" .-> L4
```

Nothing above layer 4 can send raw motor commands. That is the safety story for the pitch.

## 3. Sequence: "I want to eat rice" (full scenario)

```mermaid
sequenceDiagram
    autonumber
    actor P as Person
    participant V as Voice (D)
    participant C as Claude (B)
    participant T as Robot tools
    participant M as Mouth tracker (C)
    participant R as Arm + cameras (A)

    P->>V: "I want to eat rice"
    V->>C: listen() → "I want to eat rice"
    C->>T: look("table")
    T->>R: newest table frame
    R-->>C: image: zone_a grapes, zone_b rice, spoon in holder
    Note over C: rice → tool = spoon (food config)
    C->>V: say("Getting you some rice")
    V-->>P: spoken feedback

    rect rgb(235, 245, 255)
    Note over C,R: Pick the tool
    C->>T: go_to_waypoint("spoon_holder")
    T->>R: move via clear
    C->>T: set_gripper(0)
    T-->>C: holding_object
    end

    rect rgb(240, 255, 240)
    Note over C,R: Scoop
    C->>T: go_to_waypoint bowl_hover → bowl_dip → bowl_scoop → bowl_lift
    T->>R: taught scoop sequence (spoon level at the end)
    C->>T: look("gripper")
    T-->>C: rice on spoon? yes
    end

    rect rgb(255, 245, 235)
    Note over C,R: Serve (fast local loop, not Claude step by step)
    C->>T: go_to_waypoint("serve_spoon")
    C->>M: serve_to_mouth()
    loop ~10 times per second until standoff
        M->>R: gripper frame
        M->>M: mouth centre, size, open?
        M->>R: small capped nudge toward mouth
    end
    M-->>C: at standoff, mouth found
    C->>V: say("Here you go")
    P->>R: leans in, eats from spoon
    M-->>C: bite detected (mouth closed on spoon)
    M->>R: retreat slowly to serve_spoon
    end

    C->>V: listen()
    P->>V: "Now a grape"
    Note over C: grape → gripper: return spoon to holder first, then pick grape (same pattern)
```

## 4. Sequence: voice "stop" during a move

```mermaid
sequenceDiagram
    actor P as Person
    participant VS as Voice stop listener
    participant HW as Hardware bridge
    participant R as Arm
    participant C as Claude

    C->>R: (any move in progress)
    P->>VS: "Stop!"
    Note over VS: keyword hit, no Claude involved
    VS->>HW: hold(all motors)
    HW->>R: goal = present position
    Note over R: arm freezes in place<br/>torque stays ON (it must not drop)
    R-->>C: move result: not at target / held
    C->>P: say("Stopped. Tell me when to continue.")
```

Target: arm frozen within 0.5 s of the word.

## 5. Meal session: states

```mermaid
stateDiagram-v2
    [*] --> Idle: start session, arm at home
    Idle --> Listening: person speaks
    Listening --> Planning: request text
    Planning --> Idle: food not on table, say so
    Planning --> GetTool: needs spoon / fork
    Planning --> Pick: gripper food
    GetTool --> Pick: tool held
    Pick --> Pick: missed, look and retry once
    Pick --> Serve: holding food
    Serve --> Handover: at standoff, mouth open
    Serve --> Retreat: face lost
    Handover --> Retreat: bite detected
    Retreat --> Listening: "another one" / new request
    Retreat --> Done: "I'm done"
    Done --> [*]: tools back, arm home

    Idle --> Stopped: "stop"
    Pick --> Stopped: "stop"
    Serve --> Stopped: "stop"
    Handover --> Stopped: "stop"
    Stopped --> Listening: "continue"
```

## 6. Table layout (fixed zones)

```mermaid
flowchart TB
    subgraph TABLE["Table, seen from the table camera — mark zones with tape"]
        direction LR
        ZA["zone_a<br/>plate: grapes"]
        ZB["zone_b<br/>bowl: rice"]
        SH["spoon_holder"]
        BOX["box<br/>(stage 1 target)"]
    end
    ARM(["Arm base"])
    PERSON(["Person<br/>serve / serve_spoon poses<br/>in front of the face"])
    ARM --- TABLE
    ARM --- PERSON
```

Each zone has taught poses (`zone_a_hover`, `zone_a`, ...). Claude decides *what is in which zone*;
the waypoints decide *how to get there*.

## 7. Build order and who does what

```mermaid
flowchart LR
    subgraph MUST["Must"]
        S1["Stage 1<br/>grape pick-and-place<br/>A + B"]
        S2["Stage 2<br/>grape to mouth<br/>C + A"]
    end
    subgraph SHOULD["Should"]
        S3["Stage 3<br/>voice in/out + voice stop<br/>D"]
        S4["Stage 4<br/>food recognition + tool choice<br/>B"]
    end
    subgraph COULD["Could"]
        S5["Stage 5<br/>spoon + rice<br/>A + C"]
        S6["Stage 6<br/>whole meal<br/>B"]
    end
    S1 --> S2 --> S4
    S3 --> S4
    S4 --> S5 --> S6
    S2 --> S5
```

```mermaid
gantt
    title Hackathon timeline
    dateFormat  YYYY-MM-DD HH:mm
    axisFormat  %a %H:%M
    section A Arm
    Cameras, gripper, teach zones      :a1, 2026-11-21 14:00, 3h
    Pick-and-place runs, serve pose    :a2, after a1, 4h
    Face runs, spoon waypoints         :a3, 2026-11-22 09:00, 3h
    section B Brain
    Grasp width, pick prompt           :b1, 2026-11-21 14:00, 3h
    Food config, scan_table, planning  :b2, after b1, 4h
    End-to-end + meal loop             :b3, 2026-11-22 09:00, 3h
    section C Mouth
    Mouth tracker on webcam            :c1, 2026-11-21 14:00, 3h
    find_mouth, serve_to_mouth         :c2, after c1, 4h
    Handover, bite detection           :c3, 2026-11-22 09:00, 3h
    section D Voice + demo
    Speech-to-text, listen, props      :d1, 2026-11-21 14:00, 3h
    Voice stop, say, recordings        :d2, after d1, 4h
    Integrate, rehearse, backup video  :d3, 2026-11-22 09:00, 3h
    section Team
    Checkpoint                         :milestone, 2026-11-21 16:00, 0m
    Checkpoint                         :milestone, 2026-11-21 19:00, 0m
    Checkpoint + spoon decision        :milestone, 2026-11-22 09:00, 0m
    Code freeze                        :milestone, 2026-11-22 12:00, 0m
```
