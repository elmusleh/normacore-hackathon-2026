### Post-Implementation Suggestions

1. Pre-clone `norma-core/norma-core` repository locally on your laptop tonight — Priority 95% (Critical) [Best practices]
   What: Clone the official open-source repository `https://github.com/norma-core/norma-core` onto your laptop while on stable home internet.
   Why: Hackathon venue Wi-Fi is often slow or congested. Having the full repository offline lets you inspect `software/station/` and `shared/gremlin_py/` immediately on Saturday morning.
   How: Run `git clone https://github.com/norma-core/norma-core.git` into your workspace or dev folder.
   Status: ⏳ Unimplemented
   Reason Deferred: Awaiting user execution on host with active internet access.

2. Verify local Python dependencies and run the offline test suite — Priority 92% (Critical) [Best practices]
   What: Run `pip install -r requirements.txt` and execute `pytest tests/test_pipeline.py` on your machine.
   Why: Ensures your Python environment (especially NumPy and OpenCV/Pillow) is 100% verified and all 5 unit/integration tests pass before traveling.
   How: Run `pip install -r requirements.txt && pytest tests/test_pipeline.py -v`.
   Status: ⏳ Unimplemented
   Reason Deferred: Verification step for user's terminal environment before traveling.

3. Verify `.mcp.json` tool discovery in Claude Code or Cursor — Priority 88% (High value) [Best practices]
   What: Open this repository in Claude Code or Cursor and confirm that the `normacore-robot` MCP server is detected and tools are available.
   Why: Auto-registering tools means your AI agent can call `get_calibrated_view`, `pick_at`, and `verify_grasp` directly without manual command-line flags.
   How: Run `claude mcp list` or inspect Cursor Settings -> MCP Servers.
   Status: ⏳ Unimplemented
   Reason Deferred: Requires testing within user's specific editor/agent UI.

4. Pack essential hardware accessories: USB-A/C adapters, powered hub, and masking tape — Priority 82% (High value) [Professionalism]
   What: Put a USB-C to USB-A adapter, a 2m USB extension cable, and a small roll of masking tape into your hackathon backpack.
   Why: In live robotics hackathons, desk outlets and laptop port arrangements are unpredictable. Masking tape is invaluable for taping down AprilTags and marking bin boundaries.
   How: Pack these physical items in your travel bag tonight.
   Status: ⏳ Unimplemented
   Reason Deferred: Physical packing task before departure for Berlin.

5. Pre-download Python wheels and Protobuf packages offline — Priority 78% (High value) [Reliability]
   What: Download cached pip wheels for your environment (`pip download -r requirements.txt -d ./pip_cache`) so you can reinstall without internet.
   Why: If venue internet drops or restricts PyPI access on Saturday, you can install any missing package locally from cache.
   How: Run `pip download -r requirements.txt -d ./pip_cache`.
   Status: ⏳ Unimplemented
   Reason Deferred: Preventive measure to run before leaving home Wi-Fi.

6. Bookmark NormaCore Station Web console default URL and offline docs — Priority 70% (Nice to have) [Professionalism]
   What: Bookmark `http://localhost:8000` (or Station's default port) and save the Station README as an offline PDF.
   Why: Gives you instant access to manual motor calibration controls and joint sliders during the first 30 minutes of hardware bring-up.
   How: Save the Station docs locally in `docs/`.
   Status: ⏳ Unimplemented
   Reason Deferred: Optional convenience step ahead of kickoff.
