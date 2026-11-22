#!/usr/bin/env python3
"""Generate a use-case & human-impact focused presentation for CareArm (Team 6).

Outputs:
    docs/CareArm_Use_Case_Pitch.pptx
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

# Color Palette — Warm, Human-Centered Healthcare & Assistive Tech
CHARCOAL = RGBColor(0x11, 0x18, 0x27)
CHARCOAL_CARD = RGBColor(0x1B, 0x24, 0x36)
CHARCOAL_BORDER = RGBColor(0x2D, 0x3A, 0x52)

BG_WARM = RGBColor(0xFA, 0xF9, 0xF6)     # Warm ivory canvas
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
BORDER_SOFT = RGBColor(0xE5, 0xE7, 0xEB)
SURFACE_SOFT = RGBColor(0xF3, 0xF4, 0xF6)

TEXT_DARK = RGBColor(0x11, 0x18, 0x27)
TEXT_MUTED = RGBColor(0x4B, 0x55, 0x63)
TEXT_LIGHT = RGBColor(0xF9, 0xFA, 0xFB)
TEXT_SUB_LIGHT = RGBColor(0x9C, 0xA3, 0xAF)

TEAL = RGBColor(0x0F, 0x76, 0x6E)       # Primary care & trust
TEAL_BRIGHT = RGBColor(0x2D, 0xD4, 0xBF)
TEAL_SOFT = RGBColor(0xF0, 0xFD, 0xFA)

CORAL = RGBColor(0xEA, 0x58, 0x0C)      # Human warmth & urgency
CORAL_SOFT = RGBColor(0xFF, 0xF7, 0xED)

SAGE = RGBColor(0x05, 0x96, 0x69)       # Independence & safety confirmation
SAGE_SOFT = RGBColor(0xEC, 0xFD, 0xF5)

INDIGO = RGBColor(0x43, 0x38, 0xCA)     # Conversational AI
INDIGO_SOFT = RGBColor(0xEE, 0xF2, 0xFF)

AMBER = RGBColor(0xB4, 0x53, 0x09)
AMBER_SOFT = RGBColor(0xFF, 0xFB, 0xEB)

FONT_NAME = "Inter"


def set_bg(slide, color: RGBColor) -> None:
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = color


def add_notes(slide, text: str) -> None:
    slide.notes_slide.notes_text_frame.text = text.strip()


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
    line_spacing: float = 1.18,
):
    tb = slide.shapes.add_textbox(left, top, width, height)
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = valign
    tf.margin_left = Inches(0.04)
    tf.margin_right = Inches(0.04)
    tf.margin_top = Inches(0.02)
    tf.margin_bottom = Inches(0.02)

    for idx, line in enumerate(text.split("\n")):
        p = tf.paragraphs[0] if idx == 0 else tf.add_paragraph()
        p.alignment = align
        p.line_spacing = line_spacing
        r = p.add_run()
        r.text = line
        r.font.name = FONT_NAME
        r.font.size = Pt(font_size)
        r.font.bold = bold
        r.font.color.rgb = color
    return tb


def add_bullets(
    slide,
    left,
    top,
    width,
    height,
    items: list[tuple[str, str]],
    font_size: int = 13.5,
    text_color: RGBColor = TEXT_DARK,
    muted_color: RGBColor = TEXT_MUTED,
    bullet_char: str = "• ",
    bullet_color: RGBColor = TEAL,
    space_after: int = 10,
):
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
        p.line_spacing = 1.22

        rb = p.add_run()
        rb.text = bullet_char
        rb.font.name = FONT_NAME
        rb.font.size = Pt(font_size)
        rb.font.bold = True
        rb.font.color.rgb = bullet_color

        if lead:
            rl = p.add_run()
            rl.text = lead + " "
            rl.font.name = FONT_NAME
            rl.font.size = Pt(font_size)
            rl.font.bold = True
            rl.font.color.rgb = text_color

        r = p.add_run()
        r.text = body
        r.font.name = FONT_NAME
        r.font.size = Pt(font_size)
        r.font.bold = False
        r.font.color.rgb = muted_color if lead else text_color
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
    font_size: int = 10.5,
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
    r = p.add_run()
    r.text = text
    r.font.name = FONT_NAME
    r.font.size = Pt(font_size)
    r.font.bold = True
    r.font.color.rgb = text_color
    return shape


def add_card(
    slide,
    left,
    top,
    width,
    height,
    accent_color: RGBColor | None = None,
    bg_color: RGBColor = WHITE,
    border_color: RGBColor = BORDER_SOFT,
):
    card = add_rect(slide, left, top, width, height, bg_color, border_color, line_pt=1.0, rounded=True)
    if accent_color is not None:
        add_rect(slide, left + Inches(0.16), top, width - Inches(0.32), Inches(0.06), accent_color)
    return card


def add_header(slide, eyebrow: str, title: str, subtitle: str, slide_num: int, total: int = 9):
    set_bg(slide, BG_WARM)
    add_rect(slide, Inches(0), Inches(0), SLIDE_W, Inches(0.08), TEAL)

    add_textbox(slide, Inches(0.65), Inches(0.30), Inches(7.0), Inches(0.28), eyebrow.upper(), font_size=11, color=TEAL, bold=True)
    add_textbox(slide, Inches(0.65), Inches(0.56), Inches(12.0), Inches(0.55), title, font_size=27, color=TEXT_DARK, bold=True)
    add_textbox(slide, Inches(0.65), Inches(1.13), Inches(12.0), Inches(0.38), subtitle, font_size=14, color=TEXT_MUTED)

    # Footer
    add_rect(slide, Inches(0.65), Inches(7.02), Inches(12.03), Inches(0.015), BORDER_SOFT)
    add_textbox(
        slide,
        Inches(0.65),
        Inches(7.08),
        Inches(9.0),
        Inches(0.30),
        "CareArm (Team 6)  ·  Use-Case & Human Impact Pitch  ·  Berlin Robotics & AI Hackathon 2026",
        font_size=10,
        color=TEXT_MUTED,
    )
    add_textbox(
        slide,
        Inches(11.5),
        Inches(7.08),
        Inches(1.18),
        Inches(0.30),
        f"{slide_num} / {total}",
        font_size=10,
        color=TEXT_MUTED,
        bold=True,
        align=PP_ALIGN.RIGHT,
    )


def build_deck(output_path: Path) -> None:
    prs = Presentation()
    prs.slide_width = SLIDE_W
    prs.slide_height = SLIDE_H
    blank = prs.slide_layouts[6]
    total = 9

    # =========================================================================
    # SLIDE 1: TITLE — HUMAN-FIRST OPENING
    # =========================================================================
    s1 = prs.slides.add_slide(blank)
    set_bg(s1, CHARCOAL)
    add_rect(s1, Inches(0), Inches(0), Inches(0.22), SLIDE_H, TEAL_BRIGHT)
    add_rect(s1, Inches(9.25), Inches(0), Inches(4.083), SLIDE_H, CHARCOAL_CARD)
    add_rect(s1, Inches(9.25), Inches(0), Inches(0.03), SLIDE_H, CHARCOAL_BORDER)

    add_pill(
        s1,
        Inches(0.85),
        Inches(0.82),
        Inches(5.9),
        Inches(0.42),
        "TEAM 6 · CAREARM  |  USE-CASE & IMPACT PITCH",
        RGBColor(0x13, 0x2F, 0x2F),
        TEAL_BRIGHT,
        font_size=10.5,
        border_color=TEAL,
    )

    add_textbox(
        s1,
        Inches(0.85),
        Inches(1.58),
        Inches(8.0),
        Inches(1.65),
        "Eating Independently\nIs a Human Right.",
        font_size=50,
        color=WHITE,
        bold=True,
        line_spacing=1.08,
    )

    add_textbox(
        s1,
        Inches(0.85),
        Inches(3.45),
        Inches(7.85),
        Inches(0.95),
        "Hands-free, voice-controlled assistive feeding — designed around\nthe dignity, comfort, and pace of the person at the table.",
        font_size=17.5,
        color=TEXT_SUB_LIGHT,
        line_spacing=1.35,
    )

    # Highlight quote
    add_rect(s1, Inches(0.85), Inches(4.78), Inches(7.75), Inches(0.92), CHARCOAL_CARD, CHARCOAL_BORDER, rounded=True)
    add_rect(s1, Inches(0.85), Inches(4.90), Inches(0.08), Inches(0.68), CORAL)
    add_textbox(
        s1,
        Inches(1.12),
        Inches(4.94),
        Inches(7.35),
        Inches(0.62),
        '“Just say what you want to eat. CareArm sees your plate, picks it gently,\n and waits patiently until you open your mouth.”',
        font_size=14,
        color=TEXT_LIGHT,
        line_spacing=1.28,
    )

    add_textbox(
        s1,
        Inches(0.85),
        Inches(6.05),
        Inches(7.9),
        Inches(0.36),
        "Team 6 (CareArm):  Jan Schulz  ·  Jafer Sharfeddin  ·  Mohammad El-Musleh",
        font_size=13.5,
        color=TEXT_LIGHT,
        bold=True,
    )
    add_textbox(
        s1,
        Inches(0.85),
        Inches(6.43),
        Inches(7.9),
        Inches(0.35),
        "NormaCore Track  ·  Berlin Robotics & AI Hackathon  ·  November 22, 2026",
        font_size=12,
        color=TEXT_SUB_LIGHT,
    )

    # Right column — Why It Matters At A Glance
    add_textbox(s1, Inches(9.65), Inches(0.88), Inches(3.3), Inches(0.32), "HUMAN IMPACT AT A GLANCE", font_size=11, color=TEAL_BRIGHT, bold=True)
    highlights = [
        ("1,095 Meals / Yr", "Every day, 3 meals depend on someone else’s schedule.", CORAL),
        ("100% Hands-Free", "Natural voice (EN/DE) + mouth-open cue. Zero switches.", TEAL_BRIGHT),
        ("5–10 cm Standoff", "The robot never forces a bite — the diner leads.", SAGE),
        ("10× Affordable", "Built on open hardware vs. $6,000–$12,000+ feeders.", INDIGO),
    ]
    for i, (big, sub, col) in enumerate(highlights):
        y = Inches(1.42 + i * 1.32)
        add_rect(s1, Inches(9.65), y, Inches(3.25), Inches(1.12), CHARCOAL, CHARCOAL_BORDER, rounded=True)
        add_rect(s1, Inches(9.65), y + Inches(0.16), Inches(0.07), Inches(0.80), col)
        add_textbox(s1, Inches(9.88), y + Inches(0.12), Inches(2.88), Inches(0.38), big, font_size=20, color=WHITE, bold=True)
        add_textbox(s1, Inches(9.88), y + Inches(0.52), Inches(2.88), Inches(0.52), sub, font_size=11.5, color=TEXT_SUB_LIGHT, line_spacing=1.22)

    add_notes(
        s1,
        """Imagine being completely sharp mentally, sitting at a dinner table with friends or family—and having to ask someone else for every single bite of food, 3 times a day, over a thousand meals a year.
That is the reality for millions of people living with upper-limb paralysis, ALS, stroke recovery, or neuromuscular conditions.
We built CareArm to give people back something fundamental: the dignity to eat what they want, when they want, at their own pace.""",
    )

    # =========================================================================
    # SLIDE 2: WHO WE BUILD FOR (3 HUMAN PERSONAS)
    # =========================================================================
    s2 = prs.slides.add_slide(blank)
    add_header(
        s2,
        "01 · Who Needs CareArm",
        "Three Real Groups Directly Impacted Every Single Day",
        "Assistive feeding isn’t a niche robotics demo — it solves an exhausting daily bottleneck for patients and caregivers alike.",
        2,
        total,
    )

    personas = [
        (
            "INDIVIDUALS WITH PARALYSIS",
            "Upper-Limb Mobility Loss",
            CORAL,
            CORAL_SOFT,
            "Spinal cord injury, ALS, cerebral palsy, muscular dystrophy",
            [
                ("Autonomy at the table:", "Choose which food comes next instead of accepting whatever is handed over."),
                ("Eat at your own pace:", "Pause to talk, chew, or rest without feeling rushed by a busy helper."),
                ("Zero wearable gear:", "No chin-switches, bite-sticks, or joysticks required — just your voice."),
            ],
        ),
        (
            "POST-STROKE & REHAB PATIENTS",
            "Home Recovery",
            TEAL,
            TEAL_SOFT,
            "Temporary or long-term arm weakness after stroke or trauma",
            [
                ("Lower anxiety:", "Predictable, slow movement with clear spoken updates before every action."),
                ("10-second setup:", "1-click closed/open mouth calibration adapts to facial asymmetry."),
                ("Smooth transition home:", "Supports safe independent snacks and meals between therapy sessions."),
            ],
        ),
        (
            "CAREGIVERS & CARE STAFF",
            "Relieving Daily Burnout",
            INDIGO,
            INDIGO_SOFT,
            "Family caregivers, rehab nurses, assisted-living teams",
            [
                ("45–60 min per meal:", "Manual feeding is one of the most time-intensive daily care tasks."),
                ("Shared meals again:", "Family members can eat their own warm dinner alongside their loved one."),
                ("Scalable support:", "Frees nurses to focus on human connection and clinical care."),
            ],
        ),
    ]

    cw = Inches(3.82)
    cgap = Inches(0.285)
    for i, (tag, title, col, soft, sub, items) in enumerate(personas):
        x = Inches(0.65) + i * (cw + cgap)
        add_card(s2, x, Inches(1.75), cw, Inches(5.0), accent_color=col)
        add_pill(s2, x + Inches(0.22), Inches(1.98), cw - Inches(0.44), Inches(0.30), tag, soft, col, font_size=9.5)
        add_textbox(s2, x + Inches(0.22), Inches(2.38), cw - Inches(0.44), Inches(0.38), title, font_size=18, color=TEXT_DARK, bold=True)
        add_textbox(s2, x + Inches(0.22), Inches(2.76), cw - Inches(0.44), Inches(0.44), sub, font_size=11.5, color=col, bold=False, line_spacing=1.2)
        add_rect(s2, x + Inches(0.22), Inches(3.28), cw - Inches(0.44), Inches(0.015), BORDER_SOFT)
        add_bullets(s2, x + Inches(0.22), Inches(3.42), cw - Inches(0.44), Inches(3.15), items, font_size=12.5, bullet_color=col, space_after=11)

    add_notes(
        s2,
        """CareArm serves three real groups.
First, people living with upper-limb paralysis from spinal cord injury, ALS, or cerebral palsy—who want the freedom to choose their own bite and eat at their own pace.
Second, post-stroke and rehabilitation patients rebuilding independence at home, who benefit from 10-second per-user mouth calibration.
And third, family caregivers and nurses—who often spend 45 to 60 minutes per meal hand-feeding, and rarely get to eat a warm meal together with their loved one.""",
    )

    # =========================================================================
    # SLIDE 3: BEFORE VS WITH CAREARM
    # =========================================================================
    s3 = prs.slides.add_slide(blank)
    add_header(
        s3,
        "02 · The Transformation",
        "What Mealtime Looks Like: Today vs. With CareArm",
        "Moving from passive, scheduled dependency to conversational, self-paced independence.",
        3,
        total,
    )

    # Left Card: Today
    add_card(s3, Inches(0.65), Inches(1.78), Inches(5.85), Inches(4.95), accent_color=CORAL)
    add_pill(s3, Inches(0.95), Inches(2.02), Inches(2.4), Inches(0.32), "TODAY’S REALITY", CORAL_SOFT, CORAL, font_size=10)
    add_textbox(s3, Inches(0.95), Inches(2.44), Inches(5.25), Inches(0.42), "Dependent & Rigid", font_size=21, color=TEXT_DARK, bold=True)
    add_bullets(
        s3,
        Inches(0.95),
        Inches(2.98),
        Inches(5.25),
        Inches(3.5),
        [
            ("Waiting on schedules:", "You eat only when a caregiver or nurse has a 45-minute window."),
            ("No spontaneous choice:", "Asking repeatedly for “a grape, then chocolate” feels awkward and burdensome."),
            ("Clunky legacy feeders:", "$6k–$12k commercial arms force users to tap chin-switches to rotate a fixed bowl blindly."),
            ("Social discomfort:", "Being hand-fed in front of guests or family erodes privacy and confidence."),
        ],
        font_size=13.5,
        bullet_char="✕ ",
        bullet_color=CORAL,
        space_after=13,
    )

    # Right Card: With CareArm
    add_card(s3, Inches(6.82), Inches(1.78), Inches(5.86), Inches(4.95), accent_color=SAGE)
    add_pill(s3, Inches(7.12), Inches(2.02), Inches(2.4), Inches(0.32), "WITH CAREARM", SAGE_SOFT, SAGE, font_size=10)
    add_textbox(s3, Inches(7.12), Inches(2.44), Inches(5.25), Inches(0.42), "Natural, Safe & Self-Paced", font_size=21, color=TEXT_DARK, bold=True)
    add_bullets(
        s3,
        Inches(7.12),
        Inches(2.98),
        Inches(5.25),
        Inches(3.5),
        [
            ("Eat whenever you want:", "Hands-free voice activation — just speak in English or German."),
            ("Real food choice:", "Ask for grapes or chocolate; CareArm visually sees your plate and picks what you asked for."),
            ("You control every bite:", "The arm pauses 5–10 cm away and waits until you open your mouth."),
            ("Instant peace of mind:", "Say “Stop!” or turn your head away — CareArm freezes safely in under half a second."),
        ],
        font_size=13.5,
        bullet_char="✓ ",
        bullet_color=SAGE,
        space_after=13,
    )

    add_notes(
        s3,
        """Compare the two experiences side by side.
Today, eating means waiting for someone's schedule, feeling awkward asking for specific bites, or struggling with a $10,000 chin-switch feeder that just scoops blindly.
With CareArm, you simply speak naturally—'Give me a grape'—the arm sees what's on the table, holds the bite respectfully 5 to 10 cm in front of you, and waits until you open your mouth.""",
    )

    # =========================================================================
    # SLIDE 4: A REAL MEALTIME MOMENT (4-SCENE STORYBOARD)
    # =========================================================================
    s4 = prs.slides.add_slide(blank)
    add_header(
        s4,
        "03 · A Real Mealtime Moment",
        "How a Single Bite Feels From the Diner’s Chair",
        "Designed to feel calm, predictable, and completely under the user’s control — never robotic or intrusive.",
        4,
        total,
    )

    scenes = [
        (
            "SCENE 1",
            "Ask Naturally",
            '“I’d like a grape.”',
            "Hands-free microphone picks up English or German naturally. A soft chime confirms CareArm heard you — no buttons to press.",
            INDIGO,
            INDIGO_SOFT,
        ),
        (
            "SCENE 2",
            "Gentle Pick",
            "“Picking a grape now.”",
            "CareArm looks at the table, picks a grape without crushing it, and double-checks its grip with the wrist camera before lifting.",
            TEAL,
            TEAL_SOFT,
        ),
        (
            "SCENE 3",
            "Respectful Wait",
            "“Ready. Open your mouth.”",
            "Stops at a comfortable 5–10 cm standoff. Never pushes forward. Waits calmly while watching for your mouth-open cue.",
            AMBER,
            AMBER_SOFT,
        ),
        (
            "SCENE 4",
            "Eat on Your Terms",
            "Mouth OPEN ✓ → Delivered",
            "The moment you open your mouth, CareArm smoothly hands over the bite and glides back — ready whenever you want the next one.",
            SAGE,
            SAGE_SOFT,
        ),
    ]

    sw = Inches(2.82)
    sgap = Inches(0.25)
    for i, (tag, heading, quote, desc, col, soft) in enumerate(scenes):
        x = Inches(0.65) + i * (sw + sgap)
        add_card(s4, x, Inches(1.80), sw, Inches(4.05), accent_color=col)
        add_pill(s4, x + Inches(0.20), Inches(2.04), Inches(1.15), Inches(0.28), tag, soft, col, font_size=9.5)
        add_textbox(s4, x + Inches(0.20), Inches(2.44), sw - Inches(0.40), Inches(0.38), heading, font_size=18, color=TEXT_DARK, bold=True)

        # Dialogue bubble
        add_rect(s4, x + Inches(0.20), Inches(2.92), sw - Inches(0.40), Inches(0.62), soft, col, line_pt=0.8, rounded=True)
        add_textbox(s4, x + Inches(0.28), Inches(2.96), sw - Inches(0.56), Inches(0.54), quote, font_size=12, color=col, bold=True, valign=MSO_ANCHOR.MIDDLE)

        add_textbox(s4, x + Inches(0.20), Inches(3.72), sw - Inches(0.40), Inches(1.95), desc, font_size=12.5, color=TEXT_MUTED, line_spacing=1.32)

        if i < len(scenes) - 1:
            arr = s4.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, x + sw + Inches(0.04), Inches(3.65), Inches(0.17), Inches(0.24))
            arr.fill.solid()
            arr.fill.fore_color.rgb = RGBColor(0x9C, 0xA3, 0xAF)
            arr.line.fill.background()

    # Bottom emotional takeaway strip
    add_rect(s4, Inches(0.65), Inches(6.05), Inches(12.03), Inches(0.75), CHARCOAL, rounded=True)
    add_textbox(
        s4,
        Inches(0.95),
        Inches(6.14),
        Inches(11.45),
        Inches(0.56),
        "Switch foods effortlessly:  “Now a piece of chocolate”  ·  Need a break? Just look away or say “Stop!” — instant, gentle pause.",
        font_size=13.5,
        color=TEXT_LIGHT,
        valign=MSO_ANCHOR.MIDDLE,
    )

    add_notes(
        s4,
        """Walk through a single bite from the diner's chair.
Scene 1: You say 'I'd like a grape.' A soft chime lets you know CareArm is listening—no need to stare at a screen.
Scene 2: CareArm tells you 'Picking a grape now,' checks the plate, grasps gently without crushing, and verifies the grip.
Scene 3: It pauses respectfully 5 to 10 cm away and says 'Ready. Open your mouth when you want the bite.'
Scene 4: Only when you open your mouth does it deliver the bite and glide back. Want chocolate next? Just ask.""",
    )

    # =========================================================================
    # SLIDE 5: DESIGNED FOR TRUST & ZERO ANXIETY NEAR THE FACE
    # =========================================================================
    s5 = prs.slides.add_slide(blank)
    add_header(
        s5,
        "04 · Human-Centered Safety",
        "Why Patients Feel Safe Letting CareArm Near Their Face",
        "Trust is earned through predictable, physical guarantees — not promises from an AI model.",
        5,
        total,
    )

    trust_cards = [
        ("You Lead Every Bite", "5–10 cm Face Standoff", SAGE,
         "CareArm never closes the final gap toward a closed mouth. The diner always initiates handover with a verified mouth-open signal."),
        ("Turn Away = Auto-Pause", "0.6 s Face-Loss Watchdog", TEAL,
         "If you cough, sneeze, or turn to talk to a family member, MediaPipe detects face-loss in 0.6 s and halts delivery safely."),
        ("One-Word Instant Freeze", "< 0.5 s Direct Voice E-Stop", CORAL,
         "Saying “Stop!” bypasses the AI completely and holds all 8 motors rigidly in place — the arm never goes limp or drops onto you."),
        ("Eyes-Free Accessibility", "Spoken Cues & Soft Chimes", INDIGO,
         "Gentle Web Audio chimes and natural voice replies announce every step so users with limited neck mobility never feel surprised."),
        ("Built for Your Face", "10-Second Per-User Calibration", AMBER,
         "1-click Capture Closed & Capture Open in the browser personalizes mouth detection to each person’s unique facial range."),
        ("Focused & Unhackable", "3-Layer Scope Guardrails", CHARCOAL,
         "Off-topic chatter or background TV never confuses the arm — a <1 ms gatekeeper keeps CareArm strictly focused on safe feeding."),
    ]

    tw = Inches(3.82)
    th = Inches(2.35)
    tgap_x = Inches(0.285)
    tgap_y = Inches(0.28)
    for i, (title, sub, col, desc) in enumerate(trust_cards):
        col_i = i % 3
        row_i = i // 3
        x = Inches(0.65) + col_i * (tw + tgap_x)
        y = Inches(1.75) + row_i * (th + tgap_y)
        add_card(s5, x, y, tw, th, accent_color=col)
        add_textbox(s5, x + Inches(0.22), y + Inches(0.20), tw - Inches(0.44), Inches(0.26), sub.upper(), font_size=10, color=col, bold=True)
        add_textbox(s5, x + Inches(0.22), y + Inches(0.48), tw - Inches(0.44), Inches(0.36), title, font_size=17, color=TEXT_DARK, bold=True)
        add_textbox(s5, x + Inches(0.22), y + Inches(0.92), tw - Inches(0.44), Inches(1.25), desc, font_size=12, color=TEXT_MUTED, line_spacing=1.30)

    add_notes(
        s5,
        """The biggest question any patient, family member, or clinician asks is: 'Can I trust a robot arm near my face?'
We designed six concrete trust guarantees specifically for human comfort.
The arm always stops at a 5 to 10 cm standoff. If you look away to talk or cough, it pauses in 0.6 seconds. Saying 'Stop!' freezes the arm in place in under half a second without ever dropping onto the diner. Soft audio chimes announce every step, 10-second calibration adapts to any face, and our sub-millisecond guardrail ensures background conversation never triggers unintended moves.""",
    )

    # =========================================================================
    # SLIDE 6: REAL-WORLD DEPLOYMENT SETTINGS
    # =========================================================================
    s6 = prs.slides.add_slide(blank)
    add_header(
        s6,
        "05 · Real-World Use Cases",
        "Where CareArm Delivers Immediate Value",
        "A compact, tabletop form factor that fits real dining rooms, clinics, and care facilities.",
        6,
        total,
    )

    settings = [
        (
            "USE CASE 1 · HOME CARE",
            "Independent Home Living",
            TEAL,
            [
                ("Dining-table footprint:", "Sits on a standard table with 3 plug-and-play USB cameras."),
                ("Snack & meal autonomy:", "Eat fruit, snacks, or meals while family members work or rest."),
                ("Family dignity:", "Spouses and children return to being family — not full-time feeders."),
            ],
        ),
        (
            "USE CASE 2 · CLINICAL REHAB",
            "Rehab & Therapy Clinics",
            INDIGO,
            [
                ("Rapid patient switching:", "1-click per-user mouth calibration takes under 10 seconds."),
                ("Bilingual support:", "Works out of the box in English and German for European clinics."),
                ("Auditable safety log:", "Live Developer Trace gives clinicians full visibility into every move."),
            ],
        ),
        (
            "USE CASE 3 · ASSISTED LIVING",
            "Assisted Living & Care",
            CORAL,
            [
                ("Solves mealtime crunch:", "Assists multiple residents simultaneously during peak lunch/dinner hours."),
                ("Social dining restored:", "Residents eat alongside peers instead of waiting alone in rooms."),
                ("Staff multiplier:", "One caregiver can supervise several CareArm stations comfortably."),
            ],
        ),
    ]

    for i, (tag, title, col, items) in enumerate(settings):
        x = Inches(0.65) + i * (cw + cgap)
        add_card(s6, x, Inches(1.78), cw, Inches(4.95), accent_color=col)
        add_textbox(s6, x + Inches(0.22), Inches(2.02), cw - Inches(0.44), Inches(0.28), tag, font_size=10.5, color=col, bold=True)
        add_textbox(s6, x + Inches(0.22), Inches(2.34), cw - Inches(0.44), Inches(0.42), title, font_size=18.5, color=TEXT_DARK, bold=True)
        add_rect(s6, x + Inches(0.22), Inches(2.86), cw - Inches(0.44), Inches(0.015), BORDER_SOFT)
        add_bullets(s6, x + Inches(0.22), Inches(3.04), cw - Inches(0.44), Inches(3.45), items, font_size=13, bullet_color=col, space_after=13)

    add_notes(
        s6,
        """CareArm fits three high-need environments right away.
At home, it fits on a normal dining table so people can enjoy snacks and meals independently while spouses or family members eat alongside them.
In rehabilitation clinics, 10-second per-patient calibration and bilingual English/German voice make it effortless to share across patients.
And in assisted living facilities, where staff shortages hit hardest at mealtimes, CareArm lets residents dine socially together while relieving staff bottlenecks.""",
    )

    # =========================================================================
    # SLIDE 7: BREAKING THE COST & USABILITY BARRIER
    # =========================================================================
    s7 = prs.slides.add_slide(blank)
    add_header(
        s7,
        "06 · Why CareArm Wins",
        "10× More Affordable — And Actually Built Around Voice & Vision",
        "Commercial assistive feeders lock families out on price while still relying on 1990s switch interfaces.",
        7,
        total,
    )

    rows = [
        ("Dimension", "Commercial Feeders (Obi / MealBuddy)", "CareArm (Team 6 · NormaCore)"),
        ("Hardware Cost", "$6,000 – $12,000+ (rarely reimbursed)", "Target < $1,000 BOM (open ElRobot hardware)"),
        ("How User Controls It", "Chin-switch, head button, or joystick", "100% hands-free EN/DE voice + Mouth-Open cue"),
        ("Food Choice & Awareness", "Blind rotation across fixed bowl compartments", "AI vision sees the plate & picks what you ask for"),
        ("Face Safety", "Fixed pre-set stop point (no face awareness)", "5–10 cm standoff + 30 FPS MediaPipe + 0.6 s watchdog"),
        ("Emergency Stop", "Physical button (hard to reach for user)", "Voice “Stop!” (<0.5 s pose-hold) + button + 12 V cutoff"),
        ("Personalization", "Manual technician adjustment", "1-click browser calibration in 10 seconds"),
    ]

    tbl_shape = s7.shapes.add_table(len(rows), 3, Inches(0.65), Inches(1.80), Inches(12.03), Inches(4.85))
    tbl = tbl_shape.table
    tbl.columns[0].width = Inches(2.65)
    tbl.columns[1].width = Inches(4.35)
    tbl.columns[2].width = Inches(5.03)

    for r_i, row in enumerate(rows):
        for c_i, val in enumerate(row):
            cell = tbl.cell(r_i, c_i)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            cell.margin_left = Inches(0.16)
            cell.margin_right = Inches(0.14)
            cell.margin_top = Inches(0.08)
            cell.margin_bottom = Inches(0.08)

            cell.fill.solid()
            if r_i == 0:
                cell.fill.fore_color.rgb = CHARCOAL
            elif c_i == 2:
                cell.fill.fore_color.rgb = TEAL_SOFT if r_i % 2 == 1 else WHITE
            else:
                cell.fill.fore_color.rgb = WHITE if r_i % 2 == 1 else SURFACE_SOFT

            p = cell.text_frame.paragraphs[0]
            p.alignment = PP_ALIGN.LEFT
            r = p.add_run()
            r.text = val
            r.font.name = FONT_NAME
            r.font.size = Pt(13 if r_i == 0 else 12.5)
            r.font.bold = (r_i == 0) or (c_i == 0) or (c_i == 2)
            if r_i == 0:
                r.font.color.rgb = WHITE
            elif c_i == 2:
                r.font.color.rgb = TEAL
            elif c_i == 0:
                r.font.color.rgb = TEXT_DARK
            else:
                r.font.color.rgb = TEXT_MUTED

    add_notes(
        s7,
        """Existing commercial feeding arms like Obi cost $6,000 to $12,000, are rarely covered by insurance, and still require tapping a chin-switch to cycle blindly through bowl compartments.
CareArm flips the equation: open NormaCore hardware brings the target cost under $1,000—10 times more accessible—while upgrading the experience to natural bilingual voice, live food vision, real-time mouth-open gating, and sub-half-second voice E-stop.""",
    )

    # =========================================================================
    # SLIDE 8: WORKING TODAY & PATH TO FULL MEALS
    # =========================================================================
    s8 = prs.slides.add_slide(blank)
    add_header(
        s8,
        "07 · Proof & Roadmap",
        "Working End-to-End Today — Scaling to Complete Daily Meals",
        "Every safety guarantee and mealtime flow is verified today, with a clear path from snacks to full hot meals.",
        8,
        total,
    )

    # Left: Proven Today
    add_card(s8, Inches(0.65), Inches(1.78), Inches(5.85), Inches(4.95), accent_color=SAGE)
    add_pill(s8, Inches(0.95), Inches(2.02), Inches(2.5), Inches(0.32), "PROVEN TODAY · LIVE DEMO", SAGE_SOFT, SAGE, font_size=10)
    add_textbox(s8, Inches(0.95), Inches(2.44), Inches(5.25), Inches(0.42), "Ready at the Table Now", font_size=20, color=TEXT_DARK, bold=True)
    add_bullets(
        s8,
        Inches(0.95),
        Inches(2.96),
        Inches(5.25),
        Inches(3.55),
        [
            ("Multi-food feeding:", "95% grape delivery reliability (zero crushed fruit) + 100% voice switching between grapes & chocolate."),
            ("Live mouth-open gating:", "30 FPS OBSBOT MediaPipe tracker with 1-click user calibration & 0.6 s face-loss watchdog."),
            ("Verified safe grasp:", "Wrist camera checks jaws in <5 ms + servo load guard prevents empty lifts."),
            ("123/123 automated tests:", "Full safety, guardrail (<1 ms), and E-stop (<0.5 s) suite verified."),
        ],
        font_size=13,
        bullet_char="✓ ",
        bullet_color=SAGE,
        space_after=12,
    )

    # Right: Path to Full Meals
    add_card(s8, Inches(6.82), Inches(1.78), Inches(5.86), Inches(4.95), accent_color=INDIGO)
    add_pill(s8, Inches(7.12), Inches(2.02), Inches(2.6), Inches(0.32), "NEXT · FULL MEAL AUTONOMY", INDIGO_SOFT, INDIGO, font_size=10)
    add_textbox(s8, Inches(7.12), Inches(2.44), Inches(5.25), Inches(0.42), "From Snacks to Every Meal", font_size=20, color=TEXT_DARK, bold=True)
    add_bullets(
        s8,
        Inches(7.12),
        Inches(2.96),
        Inches(5.25),
        Inches(3.55),
        [
            ("Next 30 Days — Utensils:", "Adaptive spoon & fork holder for rice, yogurt, pasta, and soups."),
            ("Next 30 Days — Meal Memory:", "Natural pacing commands: “another one”, “smaller bite”, “slower please”, “I’m done”."),
            ("Next 6 Months — 100% Offline AI:", "On-device edge inference for total home privacy and zero Wi-Fi reliance."),
            ("Next 6 Months — Berlin Pilot:", "Co-design & clinical safety validation with local occupational therapists."),
        ],
        font_size=13,
        bullet_char="▸ ",
        bullet_color=INDIGO,
        space_after=12,
    )

    add_notes(
        s8,
        """This isn't a concept mockup—it works today.
We achieve 95% end-to-end grape delivery with zero crushed fruit, seamless voice switching between grapes and chocolate, 30 FPS mouth-open gating, and 123 out of 123 automated tests passing.
Next, we expand from finger foods to utensils—spoons for rice, yogurt, and soup—add conversational pacing like 'slower please,' move to 100% offline edge AI for privacy, and launch a co-design pilot with occupational therapists right here in Berlin.""",
    )

    # =========================================================================
    # SLIDE 9: CLOSING — DIGNITY AT EVERY TABLE
    # =========================================================================
    s9 = prs.slides.add_slide(blank)
    set_bg(s9, CHARCOAL)
    add_rect(s9, Inches(0), Inches(0), SLIDE_W, Inches(0.10), TEAL_BRIGHT)

    add_pill(
        s9,
        Inches(4.72),
        Inches(0.85),
        Inches(3.90),
        Inches(0.42),
        "TEAM 6 · CAREARM  |  NORMACORE TRACK",
        RGBColor(0x13, 0x2F, 0x2F),
        TEAL_BRIGHT,
        font_size=10.5,
        border_color=TEAL,
    )

    add_textbox(
        s9,
        Inches(0.85),
        Inches(1.55),
        Inches(11.63),
        Inches(1.35),
        "Technology Should Give People\nTheir Independence Back.",
        font_size=44,
        color=WHITE,
        bold=True,
        align=PP_ALIGN.CENTER,
        line_spacing=1.12,
    )

    pillars = [
        ("Dignity", "Eat what you want, when you want, at your own pace — hands-free.", CORAL),
        ("Trust", "5–10 cm standoff, MediaPipe mouth gate, and <0.5 s voice E-stop.", TEAL_BRIGHT),
        ("Access", "10× more affordable than commercial feeders, built on open hardware.", SAGE),
    ]
    pw = Inches(3.72)
    pgap = Inches(0.35)
    px0 = Inches(0.73)
    for i, (head, body, col) in enumerate(pillars):
        x = px0 + i * (pw + pgap)
        add_rect(s9, x, Inches(3.38), pw, Inches(2.05), CHARCOAL_CARD, CHARCOAL_BORDER, rounded=True)
        add_rect(s9, x + Inches(0.22), Inches(3.38), pw - Inches(0.44), Inches(0.06), col)
        add_textbox(s9, x + Inches(0.24), Inches(3.62), pw - Inches(0.48), Inches(0.42), head, font_size=22, color=WHITE, bold=True)
        add_textbox(s9, x + Inches(0.24), Inches(4.12), pw - Inches(0.48), Inches(1.15), body, font_size=13.5, color=TEXT_SUB_LIGHT, line_spacing=1.35)

    add_textbox(
        s9,
        Inches(0.85),
        Inches(5.88),
        Inches(11.63),
        Inches(0.55),
        "Thank You!  Let’s Watch CareArm in Action",
        font_size=24,
        color=TEAL_BRIGHT,
        bold=True,
        align=PP_ALIGN.CENTER,
    )
    add_textbox(
        s9,
        Inches(0.85),
        Inches(6.55),
        Inches(11.63),
        Inches(0.40),
        "Team 6 (CareArm): Jan Schulz · Jafer Sharfeddin · Mohammad El-Musleh  |  Berlin Robotics & AI Hackathon · Nov 22, 2026",
        font_size=12,
        color=TEXT_SUB_LIGHT,
        align=PP_ALIGN.CENTER,
    )

    add_notes(
        s9,
        """At the end of the day, robotics isn't about moving motors—it's about giving people their independence back.
CareArm brings dignity, trust, and affordability to the dining table.
Thank you—we’d love to show you CareArm in action and answer your questions!""",
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(output_path))
    print(f"Saved use-case presentation to {output_path} ({len(prs.slides)} slides)")


if __name__ == "__main__":
    repo_root = Path(__file__).resolve().parent.parent
    build_deck(repo_root / "docs" / "pitch" / "CareArm_Use_Case_Pitch.pptx")
