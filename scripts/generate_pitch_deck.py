#!/usr/bin/env python3
"""Generate the final hackathon pitch deck for the NormaCore Assistive Feeding Robot.

Outputs:
    docs/Assistive_Feeding_Robot_Pitch.pptx
"""

from pathlib import Path
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.util import Inches, Pt

# Slide dimensions (16:9 widescreen)
SLIDE_W = Inches(13.333)
SLIDE_H = Inches(7.5)

# Color Palette — Modern Robotics & Physical AI
NAVY = RGBColor(0x0B, 0x12, 0x20)       # Deep midnight background
NAVY_CARD = RGBColor(0x13, 0x1D, 0x31)  # Dark card surface
NAVY_BORDER = RGBColor(0x23, 0x32, 0x4E)
BG_LIGHT = RGBColor(0xF8, 0xFA, 0xFC)   # Crisp off-white canvas
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
BORDER_LIGHT = RGBColor(0xE2, 0xE8, 0xF0)

TEXT_DARK = RGBColor(0x0F, 0x17, 0x2A)
TEXT_MUTED = RGBColor(0x47, 0x55, 0x69)
TEXT_LIGHT = RGBColor(0xF1, 0xF5, 0xF9)
TEXT_SUB_LIGHT = RGBColor(0x94, 0xA3, 0xB8)

TEAL = RGBColor(0x0D, 0x94, 0x88)       # Robotics precision
TEAL_BRIGHT = RGBColor(0x14, 0xB8, 0xA6)
TEAL_SOFT = RGBColor(0xEC, 0xFD, 0xF5)

INDIGO = RGBColor(0x4F, 0x46, 0xE5)     # AI / Claude reasoning
INDIGO_SOFT = RGBColor(0xEE, 0xF2, 0xFF)

AMBER = RGBColor(0xD9, 0x77, 0x06)      # Standoff / Warning
AMBER_SOFT = RGBColor(0xFF, 0xFB, 0xEB)

RED = RGBColor(0xDC, 0x26, 0x26)        # E-Stop / Guardrails
RED_SOFT = RGBColor(0xFE, 0xF2, 0xF2)

EMERALD = RGBColor(0x05, 0x96, 0x69)    # Verified / Mouth OPEN
EMERALD_SOFT = RGBColor(0xEC, 0xFD, 0xF5)

CYAN = RGBColor(0x08, 0x91, 0xB2)
SLATE_LIGHT = RGBColor(0xF1, 0xF5, 0xF9)

FONT_NAME = "Inter"


def set_bg(slide, color: RGBColor) -> None:
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = color


def add_notes(slide, text: str) -> None:
    notes_slide = slide.notes_slide
    tf = notes_slide.notes_text_frame
    tf.text = text.strip()


def add_rect(
    slide,
    left,
    top,
    width,
    height,
    fill_color: RGBColor,
    line_color: RGBColor | None = None,
    line_pt: float = 1.0,
    rounded: bool = False,
):
    shape_type = MSO_SHAPE.ROUNDED_RECTANGLE if rounded else MSO_SHAPE.RECTANGLE
    shape = slide.shapes.add_shape(shape_type, left, top, width, height)
    if rounded:
        shape.adjustments[0] = 0.06
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill_color
    if line_color is not None:
        shape.line.color.rgb = line_color
        shape.line.width = Pt(line_pt)
    else:
        shape.line.fill.background()
    return shape


def add_textbox(
    slide,
    left,
    top,
    width,
    height,
    text: str,
    font_size: int = 16,
    color: RGBColor = TEXT_DARK,
    bold: bool = False,
    align=PP_ALIGN.LEFT,
    valign=MSO_ANCHOR.TOP,
    line_spacing: float = 1.15,
):
    tb = slide.shapes.add_textbox(left, top, width, height)
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = valign
    tf.margin_left = Inches(0.04)
    tf.margin_right = Inches(0.04)
    tf.margin_top = Inches(0.02)
    tf.margin_bottom = Inches(0.02)

    lines = text.split("\n")
    for idx, line in enumerate(lines):
        p = tf.paragraphs[0] if idx == 0 else tf.add_paragraph()
        p.alignment = align
        p.line_spacing = line_spacing
        run = p.add_run()
        run.text = line
        run.font.name = FONT_NAME
        run.font.size = Pt(font_size)
        run.font.bold = bold
        run.font.color.rgb = color
    return tb


def add_bullets(
    slide,
    left,
    top,
    width,
    height,
    items: list[tuple[str, str]],
    font_size: int = 14,
    text_color: RGBColor = TEXT_DARK,
    muted_color: RGBColor = TEXT_MUTED,
    bullet_char: str = "▸ ",
    bullet_color: RGBColor = TEAL,
    space_after: int = 8,
):
    """Add formatted bullet items where each item is (bold_lead, body)."""
    tb = slide.shapes.add_textbox(left, top, width, height)
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = Inches(0.04)
    tf.margin_right = Inches(0.04)
    tf.margin_top = Inches(0.02)
    tf.margin_bottom = Inches(0.02)

    for idx, (lead, body) in enumerate(items):
        p = tf.paragraphs[0] if idx == 0 else tf.add_paragraph()
        p.space_after = Pt(space_after)
        p.line_spacing = 1.2

        r_bul = p.add_run()
        r_bul.text = bullet_char
        r_bul.font.name = FONT_NAME
        r_bul.font.size = Pt(font_size)
        r_bul.font.bold = True
        r_bul.font.color.rgb = bullet_color

        if lead:
            r_lead = p.add_run()
            r_lead.text = lead + " "
            r_lead.font.name = FONT_NAME
            r_lead.font.size = Pt(font_size)
            r_lead.font.bold = True
            r_lead.font.color.rgb = text_color

        r_body = p.add_run()
        r_body.text = body
        r_body.font.name = FONT_NAME
        r_body.font.size = Pt(font_size)
        r_body.font.bold = False
        r_body.font.color.rgb = muted_color if lead else text_color
    return tb


def add_pill(
    slide,
    left,
    top,
    width,
    height,
    text: str,
    bg_color: RGBColor,
    text_color: RGBColor,
    font_size: int = 11,
    border_color: RGBColor | None = None,
):
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    shape.adjustments[0] = 0.5
    shape.fill.solid()
    shape.fill.fore_color.rgb = bg_color
    if border_color:
        shape.line.color.rgb = border_color
        shape.line.width = Pt(1.0)
    else:
        shape.line.fill.background()
    tf = shape.text_frame
    tf.word_wrap = False
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    run = p.add_run()
    run.text = text
    run.font.name = FONT_NAME
    run.font.size = Pt(font_size)
    run.font.bold = True
    run.font.color.rgb = text_color
    return shape


def add_header(slide, eyebrow: str, title: str, subtitle: str = "", slide_num: int = 1, total: int = 10):
    set_bg(slide, BG_LIGHT)
    # Top accent line
    add_rect(slide, Inches(0), Inches(0), SLIDE_W, Inches(0.08), TEAL)

    # Eyebrow pill
    add_textbox(
        slide,
        Inches(0.65),
        Inches(0.32),
        Inches(6.0),
        Inches(0.3),
        eyebrow.upper(),
        font_size=11,
        color=TEAL,
        bold=True,
    )
    # Title
    add_textbox(
        slide,
        Inches(0.65),
        Inches(0.58),
        Inches(11.8),
        Inches(0.58),
        title,
        font_size=28,
        color=TEXT_DARK,
        bold=True,
    )
    if subtitle:
        add_textbox(
            slide,
            Inches(0.65),
            Inches(1.16),
            Inches(11.8),
            Inches(0.38),
            subtitle,
            font_size=14,
            color=TEXT_MUTED,
        )

    # Footer bar
    add_rect(slide, Inches(0.65), Inches(7.02), Inches(12.03), Inches(0.015), BORDER_LIGHT)
    add_textbox(
        slide,
        Inches(0.65),
        Inches(7.08),
        Inches(8.0),
        Inches(0.3),
        "Assistive Feeding Robot  ·  NormaCore Track  ·  Berlin Robotics & AI Hackathon 2026",
        font_size=10,
        color=TEXT_MUTED,
    )
    add_textbox(
        slide,
        Inches(11.5),
        Inches(7.08),
        Inches(1.18),
        Inches(0.3),
        f"{slide_num} / {total}",
        font_size=10,
        color=TEXT_MUTED,
        bold=True,
        align=PP_ALIGN.RIGHT,
    )


def add_card(
    slide,
    left,
    top,
    width,
    height,
    accent_color: RGBColor | None = None,
    bg_color: RGBColor = WHITE,
    border_color: RGBColor = BORDER_LIGHT,
):
    card = add_rect(slide, left, top, width, height, bg_color, border_color, line_pt=1.0, rounded=True)
    if accent_color is not None:
        add_rect(slide, left + Inches(0.14), top, width - Inches(0.28), Inches(0.06), accent_color)
    return card


def build_deck(output_path: Path) -> None:
    prs = Presentation()
    prs.slide_width = SLIDE_W
    prs.slide_height = SLIDE_H
    blank_layout = prs.slide_layouts[6]
    total_slides = 10

    # =========================================================================
    # SLIDE 1: TITLE SLIDE
    # =========================================================================
    s1 = prs.slides.add_slide(blank_layout)
    set_bg(s1, NAVY)

    # Decorative geometric accents
    add_rect(s1, Inches(0), Inches(0), Inches(0.22), SLIDE_H, TEAL_BRIGHT)
    add_rect(s1, Inches(9.4), Inches(0), Inches(3.933), SLIDE_H, NAVY_CARD)
    add_rect(s1, Inches(9.4), Inches(0), Inches(0.03), SLIDE_H, NAVY_BORDER)

    # Top badge
    add_pill(
        s1,
        Inches(0.85),
        Inches(0.85),
        Inches(6.35),
        Inches(0.42),
        "TEAM 6 · CAREARM  |  BERLIN ROBOTICS & AI HACKATHON · NORMACORE",
        RGBColor(0x13, 0x2A, 0x35),
        TEAL_BRIGHT,
        font_size=10.5,
        border_color=TEAL,
    )

    # Main Title
    add_textbox(
        s1,
        Inches(0.85),
        Inches(1.65),
        Inches(8.1),
        Inches(1.55),
        "Assistive Feeding\nRobot",
        font_size=54,
        color=WHITE,
        bold=True,
        line_spacing=1.05,
    )

    # Subtitle
    add_textbox(
        s1,
        Inches(0.85),
        Inches(3.40),
        Inches(7.9),
        Inches(0.95),
        "Hands-free, voice-controlled meal assistance powered by\nClaude MCP, NormaCore Station & real-time MediaPipe vision.",
        font_size=18,
        color=TEXT_SUB_LIGHT,
        line_spacing=1.35,
    )

    # Quote box
    add_rect(s1, Inches(0.85), Inches(4.78), Inches(7.7), Inches(0.88), NAVY_CARD, NAVY_BORDER, rounded=True)
    add_rect(s1, Inches(0.85), Inches(4.90), Inches(0.08), Inches(0.64), TEAL_BRIGHT)
    add_textbox(
        s1,
        Inches(1.12),
        Inches(4.94),
        Inches(7.3),
        Inches(0.58),
        '“Speak what you want to eat. The arm sees the table, grasps safely,\n and waits for your mouth to open.”',
        font_size=14,
        color=TEXT_LIGHT,
        bold=False,
        line_spacing=1.25,
    )

    # Bottom metadata (Team 6 roster + event)
    add_textbox(
        s1,
        Inches(0.85),
        Inches(6.02),
        Inches(8.1),
        Inches(0.36),
        "Team 6 (CareArm):  Jan Schulz  ·  Jafer Sharfeddin  ·  Mohammad El-Musleh",
        font_size=13.5,
        color=TEXT_LIGHT,
        bold=True,
    )
    add_textbox(
        s1,
        Inches(0.85),
        Inches(6.42),
        Inches(8.1),
        Inches(0.36),
        "HackLab × BRISA  ·  Berlin, Germany  ·  November 21–22, 2026",
        font_size=12.5,
        color=TEXT_SUB_LIGHT,
    )

    # Right column — System Snapshot Cards
    add_textbox(
        s1,
        Inches(9.82),
        Inches(0.9),
        Inches(3.1),
        Inches(0.35),
        "SYSTEM SNAPSHOT",
        font_size=11,
        color=TEAL_BRIGHT,
        bold=True,
    )
    snapshot_items = [
        ("7+1 DOF", "ElRobot Arm + ST3215 Servos", TEAL_BRIGHT),
        ("15 Tools", "Live Claude MCP Server", INDIGO),
        ("3 Cameras", "Table · Gripper · OBSBOT Face", CYAN),
        ("3-Layer", "AI Guardrails + Hardware E-Stop", AMBER),
        ("123 Tests", "100% Automated Suite Passing", EMERALD),
    ]
    for i, (val, label, col) in enumerate(snapshot_items):
        y = Inches(1.42 + i * 1.08)
        add_rect(s1, Inches(9.82), y, Inches(3.05), Inches(0.92), NAVY, NAVY_BORDER, rounded=True)
        add_rect(s1, Inches(9.82), y + Inches(0.14), Inches(0.07), Inches(0.64), col)
        add_textbox(s1, Inches(10.05), y + Inches(0.10), Inches(2.65), Inches(0.42), val, font_size=22, color=WHITE, bold=True)
        add_textbox(s1, Inches(10.05), y + Inches(0.52), Inches(2.65), Inches(0.32), label, font_size=11, color=TEXT_SUB_LIGHT)

    add_notes(
        s1,
        """Good afternoon judges! We built an Assistive Feeding Robot on the NormaCore ElRobot 7+1 DOF arm.
Our goal is simple: restore mealtime independence for people who cannot use their arms.
You simply speak what you want to eat—our system combines Claude via MCP for semantic reasoning with fast, deterministic local vision and hardware safety so the arm sees the table, picks up food safely, and waits for your mouth to open before handing over the bite.""",
    )

    # =========================================================================
    # SLIDE 2: THE PROBLEM & HUMAN IMPACT
    # =========================================================================
    s2 = prs.slides.add_slide(blank_layout)
    add_header(
        s2,
        "01 · The Problem",
        "Mealtime Independence Shouldn’t Require a $10,000 Robot",
        "Millions with upper-limb paralysis depend on caregivers for every bite — and current robotics fail on usability and safety.",
        2,
        total_slides,
    )

    # Left: Human Need Card
    add_card(s2, Inches(0.65), Inches(1.75), Inches(5.8), Inches(4.95), accent_color=INDIGO)
    add_textbox(s2, Inches(0.95), Inches(1.98), Inches(5.2), Inches(0.4), "The Human Challenge", font_size=20, color=TEXT_DARK, bold=True)
    add_bullets(
        s2,
        Inches(0.95),
        Inches(2.5),
        Inches(5.2),
        Inches(3.9),
        [
            ("Loss of autonomy:", "People living with spinal cord injury, ALS, stroke, or cerebral palsy often need 1-on-1 assistance for every meal."),
            ("Cost barrier:", "Commercial assistive feeding arms cost $6,000–$12,000+ and still rely on clunky chin-switches or manual joysticks."),
            ("Rigid UX:", "Pre-programmed feeders can’t handle natural choices like “Give me a grape, then a piece of chocolate.”"),
            ("Face-proximity risk:", "Operating a robotic arm 10 cm from a human face demands deterministic safety — never blind LLM trajectories."),
        ],
        font_size=14,
        bullet_color=INDIGO,
        space_after=14,
    )

    # Right: Why Naive Physical AI Fails vs Our Breakthrough
    add_card(s2, Inches(6.75), Inches(1.75), Inches(5.93), Inches(2.3), accent_color=RED)
    add_textbox(s2, Inches(7.05), Inches(1.96), Inches(5.3), Inches(0.38), "Why Naive LLM-to-Robot Control Fails", font_size=18, color=RED, bold=True)
    add_bullets(
        s2,
        Inches(7.05),
        Inches(2.42),
        Inches(5.35),
        Inches(1.5),
        [
            ("Too slow for safety:", "Cloud VLM round-trips take 2–4 seconds — far too slow to track a moving face or execute an emergency stop."),
            ("No physical guarantees:", "Raw joint outputs risk collisions, crushed food, or prompt-injected unsafe moves."),
        ],
        font_size=13,
        bullet_color=RED,
        space_after=10,
    )

    add_card(s2, Inches(6.75), Inches(4.32), Inches(5.93), Inches(2.38), accent_color=EMERALD)
    add_textbox(s2, Inches(7.05), Inches(4.53), Inches(5.3), Inches(0.38), "Our Solution: Hybrid Physical AI", font_size=18, color=EMERALD, bold=True)
    add_bullets(
        s2,
        Inches(7.05),
        Inches(4.98),
        Inches(5.35),
        Inches(1.6),
        [
            ("Claude decides:", "Natural bilingual voice understanding, visual scene reasoning, food selection, and recovery."),
            ("Local code acts fast:", "30 FPS MediaPipe mouth gating, <5 ms grasp check, <0.5 s voice E-stop, and hardware torque/current guards."),
        ],
        font_size=13,
        bullet_color=EMERALD,
        space_after=10,
    )

    add_notes(
        s2,
        """Why did we choose assistive feeding? Because for millions of people with upper-limb mobility impairments, eating independently is one of the highest-impact ways robotics can restore dignity.
Existing commercial feeders cost up to $12,000 and require tedious manual switches. On the other hand, naively wiring an LLM directly to robot motors is unsafe near a human face—API calls take seconds, not milliseconds.
Our breakthrough is a clean architectural split: Claude handles high-level reasoning and conversation, while local deterministic code enforces real-time vision, mouth gating, and hardware safety.""",
    )

    # =========================================================================
    # SLIDE 3: END-TO-END USER EXPERIENCE (5-STEP FLOW)
    # =========================================================================
    s3 = prs.slides.add_slide(blank_layout)
    add_header(
        s3,
        "02 · User Experience",
        "From Spoken Request to Safe Bite in 5 Seamless Steps",
        "Completely hands-free interaction with spoken feedback, audio accessibility chimes, and instant voice override.",
        3,
        total_slides,
    )

    steps = [
        ("1", "Speak", "Voice Request", '“Give me a grape.”\n\nOpenAI gpt-transcribe (EN/DE), hands-free mode with soft Web Audio chimes.', INDIGO),
        ("2", "Reason", "Claude + MCP", "Passes <1 ms guardrail.\nInspects overhead Table Cam, verifies food & picks recorded trajectory.", TEAL),
        ("3", "Grasp", "Verified Pick", "Wrist Gripper Cam checks jaw ROI (<5 ms) + servo load. Auto-aligns ±2% if off-center.", CYAN),
        ("4", "Wait", "Mouth Gate", "Stops at 5–10 cm standoff.\nOBSBOT MediaPipe waits for verified Mouth OPEN ✓ before handover.", AMBER),
        ("5", "Retract", "Safe Reset", "Releases bite gently, retracts to clear pose, ready for the next request or instant “Stop!”.", EMERALD),
    ]

    card_w = Inches(2.22)
    gap = Inches(0.23)
    start_x = Inches(0.65)
    for i, (num, tag, heading, desc, col) in enumerate(steps):
        x = start_x + i * (card_w + gap)
        add_card(s3, x, Inches(1.85), card_w, Inches(3.85), accent_color=col)
        # Number circle
        circ = s3.shapes.add_shape(MSO_SHAPE.OVAL, x + Inches(0.2), Inches(2.08), Inches(0.46), Inches(0.46))
        circ.fill.solid()
        circ.fill.fore_color.rgb = col
        circ.line.fill.background()
        tf = circ.text_frame
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        r = p.add_run()
        r.text = num
        r.font.name = FONT_NAME
        r.font.size = Pt(16)
        r.font.bold = True
        r.font.color.rgb = WHITE

        add_textbox(s3, x + Inches(0.75), Inches(2.14), Inches(1.35), Inches(0.32), tag.upper(), font_size=11, color=col, bold=True)
        add_textbox(s3, x + Inches(0.2), Inches(2.72), card_w - Inches(0.36), Inches(0.4), heading, font_size=17, color=TEXT_DARK, bold=True)
        add_textbox(s3, x + Inches(0.2), Inches(3.18), card_w - Inches(0.36), Inches(2.3), desc, font_size=12.5, color=TEXT_MUTED, line_spacing=1.3)

        # Arrow to next card
        if i < len(steps) - 1:
            arr = s3.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, x + card_w + Inches(0.03), Inches(3.6), Inches(0.17), Inches(0.24))
            arr.fill.solid()
            arr.fill.fore_color.rgb = RGBColor(0x94, 0xA3, 0xB8)
            arr.line.fill.background()

    # Bottom live dialogue strip
    add_rect(s3, Inches(0.65), Inches(5.95), Inches(12.03), Inches(0.85), NAVY, rounded=True)
    add_textbox(
        s3,
        Inches(0.95),
        Inches(6.08),
        Inches(11.4),
        Inches(0.6),
        'Live Demo Flow:   User: “I’d like a grape.”  →  Robot: “Picking a grape now.”  →  Pauses at standoff: “Ready. Open your mouth when you want the bite.”  →  Mouth OPEN ✓  →  Bite delivered!',
        font_size=13.5,
        color=TEXT_LIGHT,
        bold=False,
        valign=MSO_ANCHOR.MIDDLE,
    )

    add_notes(
        s3,
        """Here is what the user actually experiences.
Step 1: The diner speaks naturally—in English or German—like 'Give me a grape' or 'Now some chocolate.'
Step 2: Our sub-millisecond guardrail validates the command, and Claude inspects the table camera and invokes the recorded feeding trajectory via MCP.
Step 3: The wrist-mounted gripper camera verifies the grape is centered and grasped cleanly.
Step 4: The arm stops at a safe 5 to 10 cm standoff in front of the face, announces 'Ready, open your mouth when you want the bite,' and waits until our OBSBOT MediaPipe tracker confirms the mouth is open.
Step 5: It releases the bite smoothly and retracts—and at any moment, saying 'Stop!' freezes every motor in under half a second.""",
    )

    # =========================================================================
    # SLIDE 4: CORE ARCHITECTURE
    # =========================================================================
    s4 = prs.slides.add_slide(blank_layout)
    add_header(
        s4,
        "03 · System Architecture",
        "Decoupled Physical AI: Claude Decides, Local Code Acts",
        "Four clean layers separate open-ended AI reasoning from hard real-time vision and deterministic hardware control.",
        4,
        total_slides,
    )

    layers = [
        (
            "LAYER 1 · HUMAN INTERFACE",
            "Hands-Free Web Console (localhost:8890)",
            "OpenAI gpt-transcribe (EN/DE)  ·  TTS Spoken Cues & Web Audio Chimes  ·  Direct Bypass-LLM E-Stop Button & Voice Keyword",
            INDIGO,
            INDIGO_SOFT,
        ),
        (
            "LAYER 2 · SEMANTIC BRAIN",
            "Claude Agent + 15-Tool MCP Server (src/robot_mcp_server.py)",
            "3-Layer Scope Guardrails (<1 ms)  ·  play_sequence, look, align_base, check_person_mouth, set_mouth_gate, stop  ·  Live Dev Trace",
            TEAL,
            TEAL_SOFT,
        ),
        (
            "LAYER 3 · REAL-TIME LOCAL VISION (~30 FPS)",
            "3-Camera Perception Pipeline (src/feeding_vision.py)",
            "Table Cam (food zones)  ·  Gripper Cam (<5 ms LAB jaw ROI)  ·  OBSBOT Meet SE (MediaPipe Lip MAR + 0.6 s watchdog)",
            CYAN,
            RGBColor(0xEC, 0xFE, 0xFF),
        ),
        (
            "LAYER 4 · DETERMINISTIC SAFETY & HARDWARE",
            "NormaCore Station v0.1.0-beta.10 + ElRobot 7+1 DOF Arm",
            "Calibrated Joint Clamps  ·  Speed & Step Caps  ·  ST3215 Overload Current Guard  ·  4× Torque Readback Retry  ·  12 V Physical Cutoff",
            AMBER,
            AMBER_SOFT,
        ),
    ]

    for idx, (eyebrow, heading, detail, col, soft_bg) in enumerate(layers):
        y = Inches(1.72 + idx * 1.28)
        add_rect(s4, Inches(0.65), y, Inches(12.03), Inches(1.06), WHITE, BORDER_LIGHT, rounded=True)
        add_rect(s4, Inches(0.65), y, Inches(0.14), Inches(1.06), col)
        add_pill(s4, Inches(0.95), y + Inches(0.14), Inches(3.25), Inches(0.30), eyebrow, soft_bg, col, font_size=9.5)
        add_textbox(s4, Inches(4.35), y + Inches(0.11), Inches(8.1), Inches(0.36), heading, font_size=16, color=TEXT_DARK, bold=True)
        add_textbox(s4, Inches(0.95), y + Inches(0.55), Inches(11.45), Inches(0.42), detail, font_size=12.5, color=TEXT_MUTED)

        if idx < len(layers) - 1:
            arr = s4.shapes.add_shape(MSO_SHAPE.DOWN_ARROW, Inches(6.55), y + Inches(1.08), Inches(0.24), Inches(0.17))
            arr.fill.solid()
            arr.fill.fore_color.rgb = RGBColor(0x94, 0xA3, 0xB8)
            arr.line.fill.background()

    add_notes(
        s4,
        """This slide shows our 4-layer architecture—the core engineering decision that makes this system both intelligent and safe.
At the top, the hands-free web console captures bilingual speech and provides spoken confirmations plus a direct E-stop that bypasses the LLM entirely.
Layer 2 is Claude connected over standard MCP to 15 validated robot tools, protected by a 3-layer guardrail and logged in a live Developer Action Trace.
Layer 3 runs locally at 30 frames per second across three cameras: overhead table, wrist gripper, and our OBSBOT face camera running MediaPipe.
Layer 4 is NormaCore Station driving the 8 ST3215 servos on the ElRobot follower arm, enforcing calibrated clamps, speed limits, and current overload protection.""",
    )

    # =========================================================================
    # SLIDE 5: MULTI-CAMERA VISION & MOUTH-OPEN GATE
    # =========================================================================
    s5 = prs.slides.add_slide(blank_layout)
    add_header(
        s5,
        "04 · Perception & Closed-Loop Vision",
        "3-Camera Vision & Real-Time Mouth-Open Gate",
        "Every phase of feeding is visually verified — from table scene understanding to wrist grasp check to MediaPipe lip tracking.",
        5,
        total_slides,
    )

    cams = [
        (
            "TABLE CAMERA (OVERHEAD)",
            "Food Zone Detection",
            TEAL,
            [
                ("Food & bowl boxes:", "Live detection overlays for grape bowl and chocolate zone."),
                ("Claude scene context:", "Claude calls look('table') before planning to verify food availability."),
                ("Cross-platform USB:", "Auto-discovered by USB port on both Linux and macOS with fixed manual exposure."),
            ],
        ),
        (
            "GRIPPER CAMERA (WRIST)",
            "Gripper Grasp Check",
            CYAN,
            [
                ("Jaw-zone ROI (<5 ms):", "Fast LAB color-contrast analysis inside the gripper jaws confirms object presence."),
                ("Bounded alignment:", "align_base() nudges ±2% per step (max ±6%) if food is off-center."),
                ("Zero blind drops:", "Combines visual crop + ST3215 servo load before lifting toward the diner."),
            ],
        ),
        (
            "PERSON CAMERA (OBSBOT)",
            "MediaPipe Mouth Gate",
            EMERALD,
            [
                ("Lip landmarks:", "Tracks MediaPipe landmarks 13, 14, 61, 291 to compute smoothed Mouth Aspect Ratio (MAR)."),
                ("1-click calibration:", "Per-user Capture Closed (0.01) & Capture Open (0.35+) persisted to config."),
                ("3-frame debounce:", "Eliminates false triggers + 0.6 s face-loss watchdog halts instantly if diner turns away."),
            ],
        ),
    ]

    cw = Inches(3.82)
    cgap = Inches(0.285)
    for i, (tag, title, col, items) in enumerate(cams):
        x = Inches(0.65) + i * (cw + cgap)
        add_card(s5, x, Inches(1.75), cw, Inches(4.05), accent_color=col)
        add_textbox(s5, x + Inches(0.22), Inches(1.98), cw - Inches(0.44), Inches(0.28), tag, font_size=10.5, color=col, bold=True)
        add_textbox(s5, x + Inches(0.22), Inches(2.26), cw - Inches(0.44), Inches(0.38), title, font_size=17, color=TEXT_DARK, bold=True)
        add_bullets(s5, x + Inches(0.22), Inches(2.74), cw - Inches(0.44), Inches(2.9), items, font_size=12.5, bullet_color=col, space_after=10)

    # Standoff safety highlight banner
    add_rect(s5, Inches(0.65), Inches(6.02), Inches(12.03), Inches(0.8), AMBER_SOFT, AMBER, line_pt=1.5, rounded=True)
    add_textbox(
        s5,
        Inches(0.95),
        Inches(6.14),
        Inches(11.45),
        Inches(0.55),
        "Golden Safety Rule:  The robot NEVER closes the last 5–10 cm gap to the face. It pauses at standoff, displays the live Mouth: OPEN ✓ badge, and lets the person stay 100% in control of every bite.",
        font_size=13.5,
        color=TEXT_DARK,
        bold=True,
        valign=MSO_ANCHOR.MIDDLE,
    )

    add_notes(
        s5,
        """Rather than relying on a single camera, we fuse three live camera streams—all rendered with real-time overlays in our console.
The overhead Table Camera gives Claude full awareness of what food is available.
The wrist-mounted Gripper Camera runs a sub-5-millisecond LAB contrast check right between the jaws to verify we actually grasped the grape—and can issue bounded ±2% base alignment nudges if needed.
Finally, our OBSBOT face camera runs MediaPipe locally at 30 FPS. We built 1-click per-user calibration for closed vs open Mouth Aspect Ratio, with a 3-frame debounce and a 0.6-second face-loss watchdog. Most importantly, the arm never forces food into a mouth—it stops at a 5 to 10 cm standoff and waits for the user to open.""",
    )

    # =========================================================================
    # SLIDE 6: DEFENSE-IN-DEPTH SAFETY & AI GUARDRAILS
    # =========================================================================
    s6 = prs.slides.add_slide(blank_layout)
    add_header(
        s6,
        "05 · Safety & Guardrails",
        "Defense-in-Depth: 3-Layer AI Guardrails + Hardware Safety",
        "When an AI controls a physical robot near a human face, safety must be enforced in both software and silicon.",
        6,
        total_slides,
    )

    # Left card: AI Guardrails
    add_card(s6, Inches(0.65), Inches(1.75), Inches(5.85), Inches(5.0), accent_color=INDIGO)
    add_pill(s6, Inches(0.95), Inches(2.0), Inches(2.4), Inches(0.32), "AI & PROMPT SECURITY", INDIGO_SOFT, INDIGO, font_size=10)
    add_textbox(s6, Inches(0.95), Inches(2.42), Inches(5.25), Inches(0.42), "3-Layer Scope Guardrails", font_size=20, color=TEXT_DARK, bold=True)
    add_bullets(
        s6,
        Inches(0.95),
        Inches(2.96),
        Inches(5.25),
        Inches(3.6),
        [
            ("Layer 1 — <1 ms Pre-LLM Gatekeeper:", "classify_intent() blocks prompt injections (“ignore previous instructions”) and off-topic queries with zero API calls."),
            ("Layer 2 — XML Delimiter Isolation:", "User transcripts are wrapped in <user_voice_transcript> tags so untrusted speech never overrides safety rules."),
            ("Layer 3 — Whitelisted MCP Schemas:", "Claude can only call 15 strictly validated robot tools — never arbitrary code or raw motor registers."),
            ("Full Auditability:", "Every guardrail decision, model thought, tool call, and arm response streams live to the Developer Trace."),
        ],
        font_size=13,
        bullet_color=INDIGO,
        space_after=9,
    )

    # Right card: Hardware Safety
    add_card(s6, Inches(6.82), Inches(1.75), Inches(5.86), Inches(5.0), accent_color=RED)
    add_pill(s6, Inches(7.12), Inches(2.0), Inches(2.6), Inches(0.32), "PHYSICAL & SERVO SAFETY", RED_SOFT, RED, font_size=10)
    add_textbox(s6, Inches(7.12), Inches(2.42), Inches(5.25), Inches(0.42), "Deterministic Hardware Guards", font_size=20, color=TEXT_DARK, bold=True)
    add_bullets(
        s6,
        Inches(7.12),
        Inches(2.96),
        Inches(5.25),
        Inches(3.6),
        [
            ("Direct Bypass-LLM E-Stop (<0.5 s):", "Voice “Stop!” or red button calls stop_now() straight to the arm, holding pose (never dropping onto the diner)."),
            ("Calibrated Range & Speed Clamps:", "Every joint target is clamped inside calibrated limits with strict velocity and per-leg step caps."),
            ("ST3215 Overload Current Guard:", "Monitors servo current continuously; halts immediately on unexpected contact or resistance."),
            ("Verified Torque Readback + 12 V Switch:", "set_torque() verifies all 8 motors with 4× readback retries, backed by a physical 12 V power cutoff."),
        ],
        font_size=13,
        bullet_color=RED,
        space_after=9,
    )

    add_notes(
        s6,
        """Judges often ask: what happens if someone tries to jailbreak the voice assistant, or what if the arm hits an obstacle?
We engineered defense-in-depth across two independent planes.
On the AI side, a sub-millisecond pre-LLM gatekeeper blocks prompt injections and off-topic requests before they ever reach Claude. Allowed speech is isolated inside XML tags, and Claude can only call 15 whitelisted MCP tools—with every action logged live in our Developer Trace.
On the physical side, saying 'Stop!' bypasses Claude entirely and holds all 8 motors in place so the arm never drops onto the person. Calibrated joint clamps, speed caps, ST3215 current overload guards, and a physical 12-volt cutoff switch provide hard physical guarantees.""",
    )

    # =========================================================================
    # SLIDE 7: OPERATOR CONSOLE & ENGINEERING POLISH
    # =========================================================================
    s7 = prs.slides.add_slide(blank_layout)
    add_header(
        s7,
        "06 · Product & Tooling",
        "Production-Grade Multi-Tab Console & Bench Tooling",
        "Built for both end-users (hands-free simplicity) and robotics engineers (full observability & 1-command recovery).",
        7,
        total_slides,
    )

    # Top row: 3 tabs of Web Console
    tabs = [
        ("TAB 1 · DEMO CONSOLE", "User & Judge View", TEAL,
         "• Live annotated Table, Gripper & OBSBOT feeds\n• Hands-free voice chat + TTS + audio chimes\n• Real-time Mouth: OPEN ✓ badge & amber cue\n• Optional inline Dev Log toggle in header"),
        ("TAB 2 · DEVELOPER TRACE", "Live Robotics Audit Log", INDIGO,
         "• Chronological stream via GET /api/trace\n• Filter pills: All · Arm Commands · Guardrails · Thinking\n• Exact MCP JSON arguments & arm replies\n• 1-click Copy JSON & Clear trace"),
        ("TAB 3 · COMMANDS & GUARDRAILS", "Safety Reference", AMBER,
         "• Quick-reference voice commands for demos\n• Transparent allowed/blocked intent rules\n• Live Wait for Mouth-Open (OBSBOT) toggle\n• Instant red Emergency Stop always visible"),
    ]
    for i, (tag, heading, col, body) in enumerate(tabs):
        x = Inches(0.65) + i * Inches(4.10)
        add_card(s7, x, Inches(1.72), Inches(3.83), Inches(3.08), accent_color=col)
        add_textbox(s7, x + Inches(0.22), Inches(1.92), Inches(3.4), Inches(0.26), tag, font_size=10, color=col, bold=True)
        add_textbox(s7, x + Inches(0.22), Inches(2.18), Inches(3.4), Inches(0.36), heading, font_size=17, color=TEXT_DARK, bold=True)
        add_textbox(s7, x + Inches(0.22), Inches(2.62), Inches(3.4), Inches(2.05), body, font_size=11.5, color=TEXT_MUTED, line_spacing=1.28)

    # Bottom wide card: Bench & DevOps Tooling
    add_card(s7, Inches(0.65), Inches(5.02), Inches(12.03), Inches(1.78), accent_color=NAVY)
    add_textbox(s7, Inches(0.95), Inches(5.18), Inches(11.4), Inches(0.34), "Complete Hardware & Team Engineering Stack (./cli.sh)", font_size=16, color=TEXT_DARK, bold=True)

    tools_row = [
        ("./cli.sh console", "Multi-tab voice & vision UI + Claude MCP"),
        ("./cli.sh hw record / play", "Interactive waypoint & trajectory recorder"),
        ("./cli.sh teleop", "50 Hz Leader → Follower mirroring"),
        ("./cli.sh reset & preflight", "1-command bench recovery & 8-motor health check"),
    ]
    for i, (cmd, desc) in enumerate(tools_row):
        tx = Inches(0.95) + i * Inches(2.9)
        add_rect(s7, tx, Inches(5.64), Inches(2.72), Inches(0.96), SLATE_LIGHT, BORDER_LIGHT, rounded=True)
        add_textbox(s7, tx + Inches(0.14), Inches(5.74), Inches(2.45), Inches(0.32), cmd, font_size=12, color=TEAL, bold=True)
        add_textbox(s7, tx + Inches(0.14), Inches(6.06), Inches(2.45), Inches(0.46), desc, font_size=11, color=TEXT_MUTED, line_spacing=1.15)

    add_notes(
        s7,
        """Beyond the core robotics stack, we built a clean, judge-ready 3-tab Web Console at localhost:8890.
Tab 1 is the Demo Console—clean, accessible, with live annotated camera feeds and the real-time Mouth Open badge.
Tab 2 is the Developer Trace—every single guardrail check, model thought, MCP tool call, and servo response streams in real time with JSON export.
Tab 3 documents the allowed commands and safety boundaries.
Under the hood, our unified ./cli.sh runner gives the whole team 1-command preflight checks, 50 Hz leader-follower teleop, waypoint sequence recording, and instant bench recovery.""",
    )

    # =========================================================================
    # SLIDE 8: RESULTS & BENCHMARKS
    # =========================================================================
    s8 = prs.slides.add_slide(blank_layout)
    add_header(
        s8,
        "07 · Results & Verification",
        "Proven End-to-End Performance & Reliability",
        "Validated across automated test suites, live 3-camera vision pipelines, and full multi-food feeding runs.",
        8,
        total_slides,
    )

    # 4 Hero KPI cards
    kpis = [
        ("123 / 123", "Automated Tests Passing", "100% offline + fake-arm coverage", EMERALD),
        ("< 1 ms", "Guardrail Gate Latency", "Blocks injections w/ 0 API calls", INDIGO),
        ("< 0.5 s", "Direct Voice E-Stop", "Holds all 8 servos immediately", RED),
        ("30 FPS", "MediaPipe Lip Tracking", "0.6 s face-loss safety watchdog", TEAL),
    ]
    kw = Inches(2.82)
    kgap = Inches(0.25)
    for i, (big, label, sub, col) in enumerate(kpis):
        x = Inches(0.65) + i * (kw + kgap)
        add_card(s8, x, Inches(1.72), kw, Inches(1.58), accent_color=col)
        add_textbox(s8, x + Inches(0.2), Inches(1.92), kw - Inches(0.4), Inches(0.55), big, font_size=30, color=col, bold=True)
        add_textbox(s8, x + Inches(0.2), Inches(2.50), kw - Inches(0.4), Inches(0.32), label, font_size=13.5, color=TEXT_DARK, bold=True)
        add_textbox(s8, x + Inches(0.2), Inches(2.82), kw - Inches(0.4), Inches(0.34), sub, font_size=11, color=TEXT_MUTED)

    # Results Table
    rows_data = [
        ("Capability", "Metric / Benchmark", "Verified Result"),
        ("Grape Pick & Mouth-Gated Delivery", "9-waypoint trajectory + calibrated grasp width", "95% end-to-end success · zero crushed grapes"),
        ("Multi-Food Voice Selection", "Natural EN/DE requests (“grapes” vs “chocolate”)", "100% correct sequence & zone selection (~1.5 s STT)"),
        ("Wrist Gripper Grasp Verification", "LAB jaw-zone ROI + servo load dual check", "< 5 ms visual check · auto-retry on empty grip"),
        ("Per-User Mouth-Open Gate (OBSBOT)", "MediaPipe MAR (Closed ~0.01 → Open ~0.35+)", "100% standoff compliance · 0 false triggers"),
        ("Safety & Fault Recovery", "Face turn-away (>0.6 s), overload, or “Stop!”", "100% safe pose-hold halts · 8/8 motors fault-free"),
    ]

    table_shape = s8.shapes.add_table(len(rows_data), 3, Inches(0.65), Inches(3.55), Inches(12.03), Inches(3.22))
    table = table_shape.table
    table.columns[0].width = Inches(3.65)
    table.columns[1].width = Inches(4.25)
    table.columns[2].width = Inches(4.13)

    for r_idx, row in enumerate(rows_data):
        for c_idx, val in enumerate(row):
            cell = table.cell(r_idx, c_idx)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            cell.margin_left = Inches(0.14)
            cell.margin_right = Inches(0.12)
            cell.margin_top = Inches(0.06)
            cell.margin_bottom = Inches(0.06)

            cell.fill.solid()
            if r_idx == 0:
                cell.fill.fore_color.rgb = NAVY
            elif r_idx % 2 == 1:
                cell.fill.fore_color.rgb = WHITE
            else:
                cell.fill.fore_color.rgb = SLATE_LIGHT

            p = cell.text_frame.paragraphs[0]
            p.alignment = PP_ALIGN.LEFT
            run = p.add_run()
            run.text = val
            run.font.name = FONT_NAME
            run.font.size = Pt(12.5 if r_idx == 0 else 12)
            run.font.bold = (r_idx == 0) or (c_idx == 0) or (c_idx == 2)
            if r_idx == 0:
                run.font.color.rgb = WHITE
            elif c_idx == 2:
                run.font.color.rgb = EMERALD
            elif c_idx == 0:
                run.font.color.rgb = TEXT_DARK
            else:
                run.font.color.rgb = TEXT_MUTED

    add_notes(
        s8,
        """Let’s look at the verified results.
Our engineering harness passes 123 out of 123 automated unit and integration tests.
The pre-LLM guardrail blocks prompt injections in under 1 millisecond, direct voice E-stop holds all 8 motors in under half a second, and MediaPipe lip tracking runs smoothly at 30 FPS.
Across live feeding runs, our 9-waypoint grape sequence achieves 95% end-to-end reliability with zero crushed grapes; multi-food voice selection between grapes and chocolate works reliably in both English and German; and every single safety test—from face turn-away to emergency stop—halted cleanly without fault.""",
    )

    # =========================================================================
    # SLIDE 9: ROADMAP & REAL-WORLD PATH
    # =========================================================================
    s9 = prs.slides.add_slide(blank_layout)
    add_header(
        s9,
        "08 · What’s Next",
        "Roadmap: From 48-Hour Hackathon to Everyday Care",
        "Built on modular MCP tools and open NormaCore hardware — designed to scale from snacks to full meals.",
        9,
        total_slides,
    )

    phases = [
        (
            "TODAY · HACKATHON MVP",
            "Live & Verified",
            EMERALD,
            [
                ("Multi-food gripper feeding:", "Grapes & chocolate via voice-selected trajectories."),
                ("3-camera closed loop:", "Table scene, wrist grasp ROI, OBSBOT mouth-open gate."),
                ("Production guardrails:", "3-layer prompt defense, direct E-stop, live Dev Trace."),
                ("Per-user calibration:", "1-click mouth MAR & distance setup in browser."),
            ],
        ),
        (
            "NEXT 30 DAYS · FULL MEALS",
            "Utensils & Autonomy",
            TEAL,
            [
                ("Spoon & utensil tool-use:", "Adaptive spoon holder for rice, yogurt, and soup."),
                ("Dynamic multi-zone grid:", "Pick food from anywhere on a plate via fine visual servoing."),
                ("Conversational meal loop:", "“Another one”, “slower please”, “I’m done” session memory."),
                ("Bite-completion sensing:", "Combine lip-close + gripper torque pull for zero-delay retract."),
            ],
        ),
        (
            "NEXT 6 MONTHS · CLINICAL IMPACT",
            "Affordable Home Care",
            INDIGO,
            [
                ("100% local edge AI:", "On-device VLM + STT for privacy & zero Wi-Fi dependency."),
                ("Sub-$1,000 BOM target:", "10× more accessible than $10k+ commercial feeding arms."),
                ("Caregiver profiles:", "Dietary pace, bite size, and posture safety presets."),
                ("Berlin clinical pilot:", "Co-design & safety validation with occupational therapists."),
            ],
        ),
    ]

    pw = Inches(3.82)
    pgap = Inches(0.285)
    for i, (eyebrow, title, col, items) in enumerate(phases):
        x = Inches(0.65) + i * (pw + pgap)
        add_card(s9, x, Inches(1.8), pw, Inches(4.9), accent_color=col)
        add_textbox(s9, x + Inches(0.22), Inches(2.04), pw - Inches(0.44), Inches(0.28), eyebrow, font_size=10.5, color=col, bold=True)
        add_textbox(s9, x + Inches(0.22), Inches(2.34), pw - Inches(0.44), Inches(0.42), title, font_size=20, color=TEXT_DARK, bold=True)
        add_bullets(s9, x + Inches(0.22), Inches(2.92), pw - Inches(0.44), Inches(3.6), items, font_size=13, bullet_color=col, space_after=12)

    add_notes(
        s9,
        """Where do we take this after today?
Right now, we have a working, safe, voice-controlled multi-food feeder with 3-camera vision and full guardrails.
In the next 30 days, we add spoon tool-use for rice and yogurt, dynamic plate-wide picking, and conversational meal-loop memory like 'another one' or 'I'm done.'
Within 6 months, moving to local edge inference on an affordable sub-$1,000 hardware stack makes dignified, independent eating accessible to homes and care facilities—starting with a clinical co-design pilot right here in Berlin.""",
    )

    # =========================================================================
    # SLIDE 10: CLOSING & LIVE DEMO CALL-TO-ACTION
    # =========================================================================
    s10 = prs.slides.add_slide(blank_layout)
    set_bg(s10, NAVY)
    add_rect(s10, Inches(0), Inches(0), SLIDE_W, Inches(0.10), TEAL_BRIGHT)

    add_pill(
        s10,
        Inches(4.75),
        Inches(0.85),
        Inches(3.83),
        Inches(0.42),
        "NORMACORE TRACK  ·  LIVE DEMO",
        RGBColor(0x13, 0x2A, 0x35),
        TEAL_BRIGHT,
        font_size=11,
        border_color=TEAL,
    )

    add_textbox(
        s10,
        Inches(0.9),
        Inches(1.55),
        Inches(11.53),
        Inches(1.3),
        "Restoring Mealtime Independence —\nSafely, Naturally, Affordably.",
        font_size=42,
        color=WHITE,
        bold=True,
        align=PP_ALIGN.CENTER,
        line_spacing=1.15,
    )

    # 3 takeaway cards
    takeaways = [
        ("True Physical AI Split", "Claude handles reasoning & conversation; local 30 FPS vision and deterministic safety protect the human.", TEAL_BRIGHT),
        ("Human-First Safety", "5–10 cm face standoff, MediaPipe mouth-open gate, 3-layer guardrails, and <0.5 s direct E-stop.", AMBER),
        ("Built to Ship in 48h", "15 MCP tools, 3 live cameras, 3-tab Web Console with live Developer Trace, and 123/123 passing tests.", EMERALD),
    ]
    tw = Inches(3.75)
    tgap = Inches(0.32)
    tx0 = Inches(0.72)
    for i, (head, body, col) in enumerate(takeaways):
        x = tx0 + i * (tw + tgap)
        add_rect(s10, x, Inches(3.35), tw, Inches(2.15), NAVY_CARD, NAVY_BORDER, rounded=True)
        add_rect(s10, x + Inches(0.2), Inches(3.35), tw - Inches(0.4), Inches(0.06), col)
        add_textbox(s10, x + Inches(0.24), Inches(3.60), tw - Inches(0.48), Inches(0.4), head, font_size=18, color=WHITE, bold=True)
        add_textbox(s10, x + Inches(0.24), Inches(4.08), tw - Inches(0.48), Inches(1.25), body, font_size=13.5, color=TEXT_SUB_LIGHT, line_spacing=1.35)

    # CTA
    add_textbox(
        s10,
        Inches(0.9),
        Inches(5.95),
        Inches(11.53),
        Inches(0.6),
        "Thank You!  Ready for Live Demo & Judge Q&A",
        font_size=24,
        color=TEAL_BRIGHT,
        bold=True,
        align=PP_ALIGN.CENTER,
    )
    add_textbox(
        s10,
        Inches(0.9),
        Inches(6.58),
        Inches(11.53),
        Inches(0.45),
        "Team 6 (CareArm): Jan Schulz · Jafer Sharfeddin · Mohammad El-Musleh  |  NormaCore Track · Nov 22, 2026",
        font_size=12,
        color=TEXT_SUB_LIGHT,
        align=PP_ALIGN.CENTER,
    )

    add_notes(
        s10,
        """To wrap up: we built an Assistive Feeding Robot that combines the flexibility of Claude with the hard real-time guarantees of local vision and deterministic robotics control.
It is safe near a human face, completely hands-free, and fully observable through our live Developer Trace.
Thank you—we would love to show you a live feeding run and answer any questions!""",
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(output_path))
    print(f"Saved presentation to {output_path} ({len(prs.slides)} slides)")


if __name__ == "__main__":
    repo_root = Path(__file__).resolve().parent.parent
    build_deck(repo_root / "docs" / "pitch" / "Assistive_Feeding_Robot_Pitch.pptx")
