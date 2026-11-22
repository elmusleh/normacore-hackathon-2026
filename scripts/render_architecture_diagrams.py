#!/usr/bin/env python3
"""Render high-DPI PNG and PDF architecture diagrams for CareArm (Team 6) via Graphviz.

Outputs:
    docs/diagrams/carearm_overview.png
    docs/diagrams/carearm_overview.pdf
    docs/diagrams/carearm_feeding_sequence.png
    docs/diagrams/carearm_feeding_sequence.pdf
"""

from __future__ import annotations

import subprocess
from pathlib import Path

OVERVIEW_DOT = r'''
digraph CareArmOverview {
    graph [
        rankdir=TB,
        fontname="Inter",
        fontsize=13,
        bgcolor="#FAF9F6",
        pad="0.4",
        nodesep="0.45",
        ranksep="0.55",
        splines=true,
        label=<<B><FONT POINT-SIZE="20" COLOR="#111827">CareArm (Team 6) — Assistive Feeding Robot System Overview</FONT></B><BR/><FONT POINT-SIZE="12" COLOR="#4B5563">Decoupled Physical AI: "Claude Decides, Local Code Acts Fast"</FONT>>,
        labelloc=t,
        labeljust=c
    ];
    node [
        shape=box,
        style="rounded,filled",
        fontname="Inter",
        fontsize=11,
        color="#CBD5E1",
        fillcolor="#FFFFFF",
        margin="0.18,0.12",
        penwidth=1.3
    ];
    edge [
        fontname="Inter",
        fontsize=9.5,
        color="#334155",
        penwidth=1.4,
        arrowsize=0.8
    ];

    User [
        label=<<B>Diner / Patient (Hands-Free)</B><BR/><FONT POINT-SIZE="10" COLOR="#475569">Paralyzed or Elderly User · Speaks Naturally (EN / DE)</FONT>>,
        fillcolor="#E0F2FE",
        color="#0284C7",
        penwidth=1.8
    ];

    subgraph cluster_L1 {
        label=<<B><FONT COLOR="#4338CA">LAYER 1 · HUMAN INTERFACE (http://localhost:8890)</FONT></B>>;
        style="rounded,filled";
        fillcolor="#EEF2FF";
        color="#818CF8";
        penwidth=1.5;

        Voice [label=<<B>Bilingual Voice I/O</B><BR/>OpenAI gpt-transcribe (EN/DE)<BR/>TTS Voice + Web Audio Chimes>];
        UI [label=<<B>3-Tab Web Console</B><BR/>Demo Console · Developer Trace<BR/>Commands &amp; Guardrails>];
        Estop [
            label=<<B><FONT COLOR="#B91C1C">Direct Emergency Stop</FONT></B><BR/>Voice "Stop!" / Red Button<BR/>(&lt;0.5 s · Bypasses LLM)>,
            fillcolor="#FEF2F2",
            color="#DC2626",
            penwidth=1.8
        ];
    }

    subgraph cluster_L2 {
        label=<<B><FONT COLOR="#0F766E">LAYER 2 · SEMANTIC BRAIN &amp; 3-LAYER AI GUARDRAILS</FONT></B>>;
        style="rounded,filled";
        fillcolor="#F0FDFA";
        color="#14B8A6";
        penwidth=1.5;

        G1 [label=<<B>Layer 1 Guardrail (&lt;1 ms)</B><BR/>classify_intent()<BR/>Blocks prompt injection &amp; off-topic>];
        Claude [label=<<B>Claude Agent Loop</B><BR/>Layer 2: &lt;user_voice_transcript&gt;<BR/>XML Delimiter Isolation>];
        Trace [label=<<B>Live Developer Trace</B><BR/>GET /api/trace JSON Audit Log<BR/>Guardrails · Thinking · Tool Calls>];
        MCP [label=<<B>Layer 3 · 15-Tool MCP Server</B><BR/>play_sequence · look · align_base<BR/>check_person_mouth · set_mouth_gate · stop>];
    }

    subgraph cluster_L3 {
        label=<<B><FONT COLOR="#0E7490">LAYER 3 · REAL-TIME LOCAL VISION (~30 FPS)</FONT></B>>;
        style="rounded,filled";
        fillcolor="#ECFEFF";
        color="#06B6D4";
        penwidth=1.5;

        CamTable [label=<<B>Table Camera (Overhead)</B><BR/>Bowl &amp; Food Zone Detection<BR/>(KD-USB · Fixed Exposure)>];
        CamGrip [label=<<B>Gripper Camera (Wrist)</B><BR/>&lt;5 ms LAB Jaw-Zone ROI<BR/>Grasp Check + ±2% align_base>];
        CamPerson [label=<<B>OBSBOT Person Camera</B><BR/>MediaPipe Face Landmarker<BR/>MAR Mouth-Open + 0.6 s Watchdog>];
    }

    subgraph cluster_L4 {
        label=<<B><FONT COLOR="#B45309">LAYER 4 · DETERMINISTIC SAFETY &amp; HARDWARE</FONT></B>>;
        style="rounded,filled";
        fillcolor="#FFFBEB";
        color="#F59E0B";
        penwidth=1.5;

        Tools [label=<<B>RobotTools &amp; Sequence Player</B><BR/>Calibrated Clamps · Speed/Step Caps<BR/>5–10 cm Face Standoff Pause>];
        Bridge [label=<<B>ElRobot Hardware Bridge</B><BR/>ST3215 Overload Current Guard<BR/>4× Torque-Off Readback Retry>];
        Station [label=<<B>NormaCore Station</B><BR/>v0.1.0-beta.10 (TCP 8888 / Web 8889)>];
        Arm [
            label=<<B>ElRobot 7+1 DOF Robotic Arm</B><BR/>Follower: 5B61034962 (12 V) · Leader: 5B61037051 (5 V)<BR/>+ Physical 12 V Emergency Cutoff Switch>,
            fillcolor="#FEF3C7",
            color="#D97706",
            penwidth=1.8
        ];
    }

    User -> Voice [label="  Speaks naturally"];
    Voice -> UI;
    UI -> G1 [label="  Transcript"];
    G1 -> Claude [label="  Allowed intent"];
    G1 -> Trace [style=dashed, color="#64748B"];
    Claude -> MCP [dir=both, label="  MCP JSON"];
    Claude -> Trace [style=dashed, color="#64748B"];
    Trace -> UI [style=dashed, color="#64748B", label="  Live audit"];

    User -> Estop [color="#DC2626", penwidth=2.0, label="  'Stop!'"];
    Estop -> Tools [color="#DC2626", penwidth=2.0, label="  stop_now()"];

    MCP -> Tools [label="  Validated tools"];
    CamTable -> Tools [label="  Scene"];
    CamGrip -> Tools [label="  Grasp ROI"];
    CamPerson -> Tools [label="  Mouth OPEN"];

    Tools -> Bridge [label="  Clamped targets"];
    Bridge -> Station [label="  Protobuf"];
    Station -> Arm [label="  8× ST3215"];
}
'''

FLOW_DOT = r'''
digraph CareArmFlow {
    graph [
        rankdir=LR,
        fontname="Inter",
        fontsize=12,
        bgcolor="#FAF9F6",
        pad="0.4",
        nodesep="0.4",
        ranksep="0.5",
        label=<<B><FONT POINT-SIZE="19" COLOR="#111827">CareArm (Team 6) — End-to-End Safe Feeding &amp; E-Stop Flow</FONT></B><BR/><FONT POINT-SIZE="11.5" COLOR="#4B5563">From spoken request to mouth-gated bite delivery — with instant &lt;0.5 s voice override</FONT>>,
        labelloc=t
    ];
    node [
        shape=box,
        style="rounded,filled",
        fontname="Inter",
        fontsize=11,
        margin="0.18,0.14",
        penwidth=1.5
    ];
    edge [
        fontname="Inter",
        fontsize=9.5,
        color="#334155",
        penwidth=1.5,
        arrowsize=0.85
    ];

    S1 [label=<<B>1. Voice Request</B><BR/>"Give me a grape"<BR/>gpt-transcribe (EN/DE)<BR/>+ soft audio chime>, fillcolor="#EEF2FF", color="#4338CA"];
    S2 [label=<<B>2. Guardrail (&lt;1 ms)</B><BR/>classify_intent()<BR/>Blocks prompt injection<BR/>&amp; off-topic chatter>, fillcolor="#F0FDFA", color="#0F766E"];
    S3 [label=<<B>3. Vision + Plan</B><BR/>Claude calls look("table")<BR/>Confirms grape bowl<BR/>Selects sequence>, fillcolor="#ECFEFF", color="#0891B2"];
    S4 [label=<<B>4. Verified Grasp</B><BR/>Gentle grip (no crush)<BR/>Wrist Cam LAB ROI (&lt;5 ms)<BR/>+ servo load check>, fillcolor="#F0FDFA", color="#0F766E"];
    S5 [label=<<B>5. Safe Standoff</B><BR/>Stops 5–10 cm from face<BR/>"Ready. Open your mouth"<BR/>OBSBOT 30 FPS MediaPipe>, fillcolor="#FFFBEB", color="#D97706"];
    S6 [label=<<B>6. Bite &amp; Reset</B><BR/>Mouth OPEN ✓ confirmed<BR/>Smooth bite handover<BR/>Retracts to safe pose>, fillcolor="#ECFDF5", color="#059669"];

    Block [label=<<B>Blocked (&lt;1 ms)</B><BR/>0 LLM API calls<BR/>Polite TTS reminder>, fillcolor="#F3F4F6", color="#6B7280"];
    Watchdog [label=<<B>Face-Loss Watchdog</B><BR/>Turn away &gt; 0.6 s<BR/>Auto-pause &amp; hold>, fillcolor="#FEF3C7", color="#B45309"];
    Estop [label=<<B><FONT COLOR="#B91C1C">Voice "Stop!" / Red Button</FONT></B><BR/>Bypasses Claude (&lt;0.5 s)<BR/>Holds all 8 servos rigidly<BR/>(Arm never drops)>, fillcolor="#FEF2F2", color="#DC2626", penwidth=2.0];

    S1 -> S2;
    S2 -> Block [label="Invalid", style=dashed, color="#6B7280"];
    S2 -> S3 [label="Valid"];
    S3 -> S4;
    S4 -> S5;
    S5 -> Watchdog [label="Face lost", style=dashed, color="#B45309"];
    S5 -> S6 [label="Mouth OPEN ✓", color="#059669", penwidth=1.8];
    Estop -> S4 [style=dashed, color="#DC2626", label="Active anytime"];
    Estop -> S5 [style=dashed, color="#DC2626"];
}
'''


def render(dot_src: str, out_base: Path) -> None:
    out_base.parent.mkdir(parents=True, exist_ok=True)
    dot_file = out_base.with_suffix(".dot")
    dot_file.write_text(dot_src.strip() + "\n", encoding="utf-8")
    subprocess.run(["dot", "-Tpng", "-Gdpi=200", str(dot_file), "-o", str(out_base.with_suffix(".png"))], check=True)
    subprocess.run(["dot", "-Tpdf", str(dot_file), "-o", str(out_base.with_suffix(".pdf"))], check=True)
    dot_file.unlink()
    print(f"Rendered {out_base.with_suffix('.png')} and {out_base.with_suffix('.pdf')}")


def main() -> None:
    diagrams_dir = Path(__file__).resolve().parent.parent / "docs" / "diagrams"
    render(OVERVIEW_DOT, diagrams_dir / "carearm_overview")
    render(FLOW_DOT, diagrams_dir / "carearm_feeding_sequence")


if __name__ == "__main__":
    main()
