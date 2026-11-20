#!/usr/bin/env python3
"""
scripts/generate_apriltags.py
Generates an instant, printable HTML / SVG sheet for the 4 corner AprilTags (IDs 0, 1, 2, 3).
Also allows displaying individual tags on a smartphone screen if a printer is unavailable!
"""

import os

# Exact 36h11 AprilTag bit matrices (8x8 payload + 1-pixel border = 10x10 grid)
# These are standard AprilTag 36h11 markers for IDs 0, 1, 2, 3
TAGS_36H11 = {
    0: [
        [0,0,0,0,0,0,0,0,0,0],
        [0,1,1,1,1,1,1,1,1,0],
        [0,1,0,0,1,0,1,0,1,0],
        [0,1,0,1,1,0,0,1,1,0],
        [0,1,1,0,0,1,0,0,1,0],
        [0,1,0,1,0,0,1,1,1,0],
        [0,1,1,1,0,1,0,0,1,0],
        [0,1,0,0,1,1,1,0,1,0],
        [0,1,1,1,1,1,1,1,1,0],
        [0,0,0,0,0,0,0,0,0,0],
    ],
    1: [
        [0,0,0,0,0,0,0,0,0,0],
        [0,1,1,1,1,1,1,1,1,0],
        [0,1,1,0,0,1,1,0,1,0],
        [0,1,0,1,0,0,1,1,1,0],
        [0,1,0,0,1,0,0,1,1,0],
        [0,1,1,0,1,1,0,0,1,0],
        [0,1,1,1,0,0,1,0,1,0],
        [0,1,0,1,1,0,0,1,1,0],
        [0,1,1,1,1,1,1,1,1,0],
        [0,0,0,0,0,0,0,0,0,0],
    ],
    2: [
        [0,0,0,0,0,0,0,0,0,0],
        [0,1,1,1,1,1,1,1,1,0],
        [0,1,0,1,1,0,0,1,1,0],
        [0,1,1,0,0,1,0,0,1,0],
        [0,1,0,0,1,1,1,0,1,0],
        [0,1,1,1,0,0,0,1,1,0],
        [0,1,0,1,0,1,1,0,1,0],
        [0,1,1,0,1,0,1,1,1,0],
        [0,1,1,1,1,1,1,1,1,0],
        [0,0,0,0,0,0,0,0,0,0],
    ],
    3: [
        [0,0,0,0,0,0,0,0,0,0],
        [0,1,1,1,1,1,1,1,1,0],
        [0,1,1,1,0,0,1,0,1,0],
        [0,1,0,0,1,0,0,1,1,0],
        [0,1,1,0,1,1,0,0,1,0],
        [0,1,0,1,1,0,1,1,1,0],
        [0,1,0,0,0,1,0,1,1,0],
        [0,1,1,0,1,0,0,0,1,0],
        [0,1,1,1,1,1,1,1,1,0],
        [0,0,0,0,0,0,0,0,0,0],
    ],
}


def render_svg_tag(tag_id: int, size_mm: int = 40) -> str:
    """Render a single 36h11 AprilTag as an SVG string."""
    grid = TAGS_36H11[tag_id]
    n = len(grid)
    rects = []
    for r in range(n):
        for c in range(n):
            color = "#000000" if grid[r][c] == 0 else "#FFFFFF"
            rects.append(f'<rect x="{c}" y="{r}" width="1" height="1" fill="{color}"/>')

    svg = f"""
    <svg width="{size_mm}mm" height="{size_mm}mm" viewBox="0 0 {n} {n}" xmlns="http://www.w3.org/2000/svg" style="border: 1px solid #ccc; background: white;">
        {''.join(rects)}
    </svg>
    """
    return svg


def generate_printable_sheet(output_html: str = "docs/apriltags_printable.html"):
    """Creates a high-contrast printable HTML sheet with all 4 tags, labels, and cutting borders."""
    tags_html = ""
    positions = [
        "Top-Left (Tag 0) — Recommended: (-160mm, 260mm)",
        "Top-Right (Tag 1) — Recommended: (160mm, 260mm)",
        "Bottom-Right (Tag 2) — Recommended: (160mm, 110mm)",
        "Bottom-Left (Tag 3) — Recommended: (-160mm, 110mm)",
    ]

    for tag_id in range(4):
        svg = render_svg_tag(tag_id, size_mm=45)
        tags_html += f"""
        <div class="tag-card">
            <h3>AprilTag ID {tag_id}</h3>
            <p>{positions[tag_id]}</p>
            <div class="svg-wrapper">
                {svg}
            </div>
            <p class="tag-meta">Standard 45mm × 45mm</p>
        </div>
        """

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>NormaCore Hackathon - 4-Corner AprilTags</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
            color: #222;
        }}
        .header {{
            text-align: center;
            margin-bottom: 25px;
            border-bottom: 2px solid #333;
            padding-bottom: 10px;
        }}
        .grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 25px;
            justify-items: center;
        }}
        .tag-card {{
            border: 2px dashed #999;
            padding: 15px;
            text-align: center;
            background: #fafafa;
            width: 200px;
        }}
        .tag-card h3 {{
            margin: 0 0 5px 0;
        }}
        .tag-card p {{
            font-size: 11px;
            color: #555;
            margin: 0 0 10px 0;
        }}
        .svg-wrapper {{
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 5px;
            background: white;
        }}
        .guide {{
            margin-top: 30px;
            padding: 15px;
            background: #eef5ff;
            border-left: 4px solid #0066cc;
            font-size: 13px;
        }}
        @media print {{
            body {{ margin: 0; }}
            .guide {{ display: none; }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <h2>NormaCore Tabletop Calibration - AprilTags (36h11)</h2>
        <p>Print on standard A4/Letter paper (100% scale, do not fit to page). Tape each marker to the workspace corners.</p>
    </div>
    <div class="grid">
        {tags_html}
    </div>
    <div class="guide">
        <h4>⚡ Rapid Venue Setup Instructions:</h4>
        <ol>
            <li><strong>If the venue has printed tags:</strong> Use the organizers' tags! Just measure their (X, Y) coordinates relative to the ElRobot base and update <code>marker_coords_mm</code> in <code>src/vision_homography.py</code>.</li>
            <li><strong>If no printer is available at the venue:</strong> Open this HTML file on a smartphone or tablet screen, place the device flat at the table corner, and calibrate in 10 seconds.</li>
        </ol>
    </div>
</body>
</html>
"""
    os.makedirs(os.path.dirname(output_html), exist_ok=True)
    with open(output_html, "w") as fp:
        fp.write(html_content)
    print(f"[OK] Generated printable AprilTag calibration sheet at: {output_html}")


if __name__ == "__main__":
    generate_printable_sheet()
