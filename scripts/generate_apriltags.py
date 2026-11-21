#!/usr/bin/env python3
"""
scripts/generate_apriltags.py
Printable HTML sheet with the 4 table-corner AprilTags (family 36h11, IDs 0-3).

The bit patterns come from OpenCV's own 36h11 dictionary (cv2.aruco), so every
AprilTag detector reads them. The sheet this script made before 2026-11-21 used
hand-typed patterns that were NOT real tags; nothing could detect them. Reprint.

Usage:
    python3 scripts/generate_apriltags.py [--size-mm 80] [--out docs/apriltags_printable.html]

Tag size = the side of the OUTER BLACK SQUARE. Measure it on the printout with a ruler
and pass that number to ./cli.sh calib camera --tag-size-mm (printers often scale).
"""

from __future__ import annotations

import argparse
import os
from typing import List

import cv2

FAMILY = "36h11"
TAG_IDS = (0, 1, 2, 3)
# Where each tag goes, looking down at the table from the person's side.
CORNERS = {0: "back-left", 1: "back-right", 2: "front-right", 3: "front-left"}


def tag_bits(tag_id: int) -> List[List[int]]:
    """8x8 grid (black border + 6x6 data) of a 36h11 tag; 1 = white, 0 = black."""
    d = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_APRILTAG_36h11)
    img = cv2.aruco.generateImageMarker(d, tag_id, 8)
    return [[1 if px > 127 else 0 for px in row] for row in img]


def render_svg_tag(tag_id: int, size_mm: float = 80.0) -> str:
    """One tag as SVG. The black square is size_mm wide; a 1-module white margin surrounds it."""
    bits = tag_bits(tag_id)
    n = len(bits)  # 8
    module_mm = size_mm / n
    total = n + 2  # white quiet zone of one module on each side
    rects = [f'<rect x="0" y="0" width="{total}" height="{total}" fill="#FFFFFF"/>']
    for r in range(n):
        for c in range(n):
            if bits[r][c] == 0:
                rects.append(f'<rect x="{c + 1}" y="{r + 1}" width="1.02" height="1.02" fill="#000000"/>')
    return (f'<svg width="{total * module_mm:.2f}mm" height="{total * module_mm:.2f}mm" '
            f'viewBox="0 0 {total} {total}" xmlns="http://www.w3.org/2000/svg" '
            f'shape-rendering="crispEdges">{"".join(rects)}</svg>')


def generate_printable_sheet(output_html: str = "docs/apriltags_printable.html", size_mm: float = 80.0) -> str:
    cards = ""
    for tag_id in TAG_IDS:
        cards += f"""
        <div class="tag-card">
            <h3>Tag {tag_id} &mdash; {CORNERS[tag_id]}</h3>
            {render_svg_tag(tag_id, size_mm)}
            <p>AprilTag {FAMILY} &middot; black square {size_mm:g} mm</p>
        </div>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Table corner AprilTags ({FAMILY}, IDs 0-3)</title>
<style>
  @page {{ size: A4; margin: 10mm; }}
  body {{ font-family: Arial, sans-serif; margin: 0; color: #222; }}
  h2 {{ font-size: 15px; margin: 0 0 4px 0; }}
  .note {{ font-size: 11px; margin: 0 0 8px 0; }}
  .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 6mm; justify-items: center; }}
  .tag-card {{ border: 1px dashed #999; padding: 3mm; text-align: center; break-inside: avoid; }}
  .tag-card h3 {{ font-size: 13px; margin: 0 0 2mm 0; }}
  .tag-card p {{ font-size: 10px; margin: 2mm 0 0 0; color: #555; }}
</style>
</head>
<body>
  <h2>Table corner AprilTags ({FAMILY}, IDs 0&ndash;3)</h2>
  <p class="note">Print at 100% (no "fit to page"). Measure the black square with a ruler and use that size.
  Keep the white margin around each tag. Tape them flat, one per table corner, IDs as labelled
  (back = far side from the person). Then measure the tag-centre distances for ./cli.sh calib.</p>
  <div class="grid">{cards}
  </div>
</body>
</html>
"""
    os.makedirs(os.path.dirname(output_html) or ".", exist_ok=True)
    with open(output_html, "w") as fp:
        fp.write(html)
    return output_html


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--size-mm", type=float, default=80.0, help="side of the black square (default 80)")
    ap.add_argument("--out", default="docs/apriltags_printable.html")
    args = ap.parse_args()
    path = generate_printable_sheet(args.out, args.size_mm)
    print(f"[OK] Wrote {path}: AprilTag {FAMILY} IDs 0-3, black square {args.size_mm:g} mm. Print at 100%.")


if __name__ == "__main__":
    main()
