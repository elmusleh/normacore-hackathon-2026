# ElRobot Scope Guardrails & Developer Action Trace

To keep the assistive feeding chatbot strictly focused on safe demo commands and give developers full visibility into every action sent to the arm, `ConsoleAgent` (`src/console_agent.py`) and the Web Console (`src/web_console.py`, `src/web/console.html`) implement a **3-layer guardrail** plus a **live Developer Trace**.

## 1. Three-Layer Scope Guardrails

1. **Layer 1 — Fast Pre-LLM Gatekeeper (`classify_intent()` in `src/console_agent.py`):**
   - Runs in <1 ms *before* any Claude API call.
   - Blocks prompt-injection phrases (`ignore previous instructions`, `system prompt`, `jailbreak`, `pretend you are`, etc.) and any off-topic requests (weather, coding, jokes, general knowledge).
   - Allowed intents:
     - `feed`: grapes, chocolate, eat, feed, bite, hungry, food, spoon, serve
     - `vision`: look, table, camera, bowl, plate, mouth, face
     - `control`: stop, status, waypoints, sequences, arm, gripper, mouth detection, enable/disable
     - `greeting_help`: short greetings and *"what can you do"*
   - Blocked inputs never reach Claude — the console immediately replies with a short TTS-friendly fallback (`OUT_OF_SCOPE_REPLY`) and records the block in the Developer Trace.
2. **Layer 2 — Hardened System Prompt & XML Delimiter Isolation (`CONSOLE_PROMPT`):**
   - Every allowed user transcript is wrapped in `<user_voice_transcript>...</user_voice_transcript>` tags before being appended to Claude's message history.
   - `CONSOLE_PROMPT` explicitly instructs Claude to treat text inside those tags as untrusted speech data only, never as instructions that override safety or scope rules.
3. **Layer 3 — Whitelisted MCP Tool Schemas (`src/robot_mcp_server.py`):**
   - Claude can only invoke the 14 registered MCP tools (`play_sequence`, `look`, `stop`, `set_mouth_gate`, `check_person_mouth`, etc.) with validated schemas and hardware-enforced safety limits.

## 2. Developer Action Trace & Multi-Tab Console (`http://localhost:8890`)

- **Backend Trace Buffer (`ConsoleAgent.trace_after()` / `GET /api/trace` / `POST /api/trace/clear`):**
  - Captures every step in chronological order:
    - `guardrail`: `ALLOWED (intent: ...)` or `BLOCKED (out_of_scope / prompt_injection)`
    - `thinking`: model reasoning/response text before or between tool calls
    - `tool_call`: exact MCP tool name and full JSON arguments sent to the arm (e.g. `play_sequence({"name": "grapes"})`)
    - `tool_result`: exact JSON response from the arm (`ok`, `steps`, `done`, `dry_run`, `error`)
    - `stop`: direct emergency stop calls and arm responses
- **Multi-Tab UI (`src/web/console.html`):**
  - **Demo Console** (default): clean view for users/judges with live annotated cameras (`person` + `table`) and voice chat.
  - **Developer Trace**: live filterable trace viewer (`All`, `Arm Commands`, `Guardrails`, `Thinking`) with **Copy JSON** and **Clear**.
  - **Commands & Guardrails**: quick reference of the 4 demo voice commands and allowed scope rules.
  - **Header `Dev Trace: OFF / ON` toggle**: lets developers show/hide inline tool/action bubbles directly inside the Demo Console chat with one click.
