# Project Preferences: NormaCore Hackathon

- **Target Hardware:** ElRobot 7+1 DOF 3D-printable robotic arm with ST3215 serial bus smart servos.
- **Runtime:** NormaCore Station (`norma-core/norma-core`, Python/Protobuf SDK `gremlin_py`, Web Console).
- **Agent Integration:** Model Context Protocol (MCP) tool server (`.mcp.json`) compatible with Claude Code, Cursor, and Codex CLI.
- **Vision Stack:** OpenCV + NumPy for perspective homography; AprilTag 36h11 fiducial markers (IDs 0–3) for millimeter coordinate calibration.
- **Python Version:** Python 3.10+ (specifically compatible with NumPy 1.26.x and Pillow).
- **Communication Style:** Clear, structured GitHub Markdown with clickable file links (`file://`).
- **Testing:** Offline mock simulation first, hardware validation second. Always test with `pytest tests/test_pipeline.py`.
