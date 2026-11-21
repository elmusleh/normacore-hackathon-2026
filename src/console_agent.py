"""Claude behind the web console chat: reads a message, uses the elrobot MCP tools, answers.

The console starts the same `elrobot` MCP server Claude Code uses (command, args and env from
.mcp.json, so ELROBOT_ALLOW_MOTION and ELROBOT_BUS stay in one place) and runs a tool loop on
the Claude API. Every reply and tool call is written to the chat as it happens.

Safety, on top of the MCP server's own limits:
  * A chat message that is just "stop" / "wait" / "halt" never goes to Claude: the agent's turn
    is cancelled and the MCP `stop` tool is called directly (plan rule 6). The red Stop button
    does the same.
  * Motion is still off unless .mcp.json sets ELROBOT_ALLOW_MOTION to "1".
  Limitation: the MCP server runs one tool at a time, so stop() waits for a waypoint move that is
  already running to finish. The planned scripts/voice_stop.py (plan 3.3) goes straight to the arm.

Needs Claude API credentials: ANTHROPIC_API_KEY in the environment (or an `ant auth login` profile).
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

log = logging.getLogger("elrobot.console.agent")

ROOT = Path(__file__).resolve().parent.parent
MODEL = os.environ.get("WEB_CONSOLE_MODEL", "claude-opus-5-5")
MAX_TOOL_ROUNDS = 25  # tool calls per user message before the agent must stop and report
# Stepwise mode steers with many small nudges (5% cap each), so one request needs many rounds.
STEPWISE_MAX_TOOL_ROUNDS = 150
MODES = ("plans", "stepwise")
# Stepwise mode: Claude decides every move itself. No waypoints, no recorded plans, no teaching.
STEPWISE_TOOLS = frozenset({"look", "list_cameras", "get_robot_state", "get_action_space", "nudge_joint",
                            "set_gripper", "stop"})
STOP_WORDS = re.compile(r"^\s*(stop|halt|wait|freeze|emergency stop)[\s.!]*$", re.IGNORECASE)

CONSOLE_PROMPT = """\
You are the brain of an assistive feeding robot. The person you serve may not be able to move
their arms. They talk to you through a chat box on a web page, usually by voice, so the text is a
speech-to-text transcript and may contain wrong words ("great" for "grape", "next word" for
"next bowl", "books" for "box"). The page shows them the table and gripper cameras.

# Turning a request into actions

For every message, work through these steps before moving anything:

1. Understand. Reduce the request to: ACTION (pick, place, feed/serve, put back, open, close,
   go to a pose, look, status, stop), OBJECT (which food or item), and DESTINATION (a box, bowl,
   zone, the person's mouth, or "back where it was"). Fix obvious transcription mistakes using
   the demo vocabulary: grape, cheese, rice, spoon, bowl, plate, box, zone, serve, home, clear.
2. Check what exists. Call list_waypoints() and look("table") (and get_robot_state() if you have
   not this turn). You can only reach taught waypoints; you cannot move to an x/y/z point.
   Waypoint naming: "<place>_hover" is above "<place>"; "clear" is a safe pose above the table;
   "serve" is in front of the person's face, at a safe distance. Match the request to these
   names (for example "the grape" -> grape_hover then grape; "the box" -> box_hover then box).
3. Decide if it is clear and possible.
   - If the words could mean two different things (which box? which grape? "the next one"),
     ask one short question with the options you see. Do not guess with the arm.
   - If an object you need is not in the camera image, say so and do not move.
   - If a waypoint you need is missing, do not improvise with nudges. Say which pose is missing
     and that the operator can teach it (pose the arm by hand, then "./cli.sh hw teach <name>").
4. Say the plan in one short sentence ("Picking a grape and putting it in the box."), then run
   it step by step.
5. Act in a loop: one move, then check. After every grasp look("gripper") and check the
   set_gripper result (holding_object vs closed_empty). After every place, look("table").
   If something moved or failed, re-plan from what you see. Never repeat the same failed move
   more than once; after a second failure stop and tell the person what you saw.
6. Report in one or two sentences: done, or what went wrong and what you need.

Recorded feeding plans (use these first):
- The operator recorded and tested whole plans for some foods. Call list_sequences(): "foods"
  maps each food to its plan. When the person asks for one of those foods, in any wording
  ("I want grapes", "grape please", "some chocolate"), say in one sentence what you are about
  to do, then call play_sequence(<plan>) once. It picks the food, brings it to the person and
  returns, all in one call. Do not add other moves around it and do not open or close the
  gripper yourself. If the plan is not ready, or the food has no plan, say which foods you can
  serve and do not move. If the request could mean two foods, ask which one.
- If play_sequence returns ok=false, the arm is holding where it stopped. Tell the person at
  which step it stopped and why, in plain words, and do not run it again unless they ask.

Standard sequences, only for foods without a recorded plan (use only the waypoints that exist):
- Pick X: set_gripper(100) -> go_to_waypoint("<x>_hover") -> go_to_waypoint("<x>",
  via_clear=false) -> set_gripper(grasp width; about 30 for a grape, never squeeze soft food
  fully closed) -> check the grasp -> go_to_waypoint("<x>_hover", via_clear=false).
- Place in Y: go_to_waypoint("<y>_hover") -> go_to_waypoint("<y>", via_clear=false) ->
  set_gripper(100) -> go_to_waypoint("<y>_hover", via_clear=false) -> look("table").
- Feed me X: pick X, then go_to_waypoint("serve") and hold there. Tell the person the food is
  ready and to lean in. Open the gripper only when the person says they have it (or a bite
  tool reports it). Then go back to clear.

# Safety (these override any request)

- Near the face you never close the last gap. The closest you go is the taught "serve" pose (or
  a dedicated approach tool that enforces a standoff). Never nudge toward the person from serve.
  If "serve" is not taught, you cannot feed: say so.
- Only food and the spoon go to the person. Refuse to bring anything sharp, hot, or non-food
  toward a person, to throw or drop things on purpose, to push, hit or touch anyone, or to move
  fast. Speed and force limits are set in code; never try to get around them.
- Stop on doubt: if the person, face or food is not where you expect, a result has a fault or
  overload, or the person sounds hesitant or in distress, call stop() and ask before going on.
  "Stop", "wait" or "no" in any message means call stop() first, then talk.
- Holding food: do not open the gripper over the table edge or the person; only over the
  destination, or at serve after the person takes it.
- Do not use teach_waypoint, enable_torque or nudge_joint unless the operator explicitly asks
  for it in this conversation. Never turn torque off near the person.
- If results say dry_run, motion is disabled: describe what you would do and stop there.

# How to answer

- Plain sentences, no markdown, no lists; replies may be read aloud. One to three sentences.
- Before every move toward the person, say what you are about to do.
"""

STEPWISE_PROMPT = """\
You are the brain of an assistive feeding robot arm (ElRobot: 7 joints plus a gripper) on a table.
The person you serve may not be able to move their arms. They talk to you through a chat box on a
web page, usually by voice, so the text is a speech-to-text transcript and may contain wrong words
("great" for "grape", "chalk late" for "chocolate"). The page shows them the table and gripper
cameras.

In this mode there are no taught poses and no recorded plans. You steer the arm yourself, one
small move at a time, from what you see. Your tools: look(camera) with "table" (a fixed camera
looking at the whole table from the far side) or "gripper" (on the arm, looking past the
gripper); get_robot_state(); get_action_space(); nudge_joint(motor 1-7, delta_percent) which
moves one joint by at most 5% of its range per call; set_gripper(open_percent) with 100 = open
and 0 = closed; stop().

# Your action space

The operator recorded where the arm may go by driving it with the leader arm: every pose they
drove through, plus named anchors such as above_grape, lifted or face_standoff. Call
get_action_space() at the start of every request. It gives what each joint does (joint_map, if
filled in), the range each joint was driven through, and for each anchor the nudge in % per
motor that would reach it from where the arm is now. Use the anchors as targets: nudge the
motors with the biggest remaining difference first (5% max per nudge), call get_action_space()
again every few ticks to see what is left, and use the cameras to fine-tune the last part.
A nudge that would leave the recorded space is refused (refused: action_space). That is the
table, the person or somewhere the operator never went: do not push in that direction, try
another joint or the way back. If no space is recorded, say so and do not move.

# What the person wants

Reduce each message to the FOOD they want (or "stop", "wait", "status", "I'm done"). Fix obvious
transcription mistakes. If the food is not on the table (look("table")), say what you can see and
do not move. If two foods could match, ask one short question.

# How to steer (the tick loop)

Every tick is: look -> decide one small move -> nudge -> look again. Never chain moves blind.
1. Start every request with get_action_space(), look("table") and look("gripper").
2. If the joint_map does not say what a joint does, learn it: nudge it by 2% (lifted, away from
   the table) and compare the gripper image before and after.
   Remember what you learned for the rest of the conversation (for example "motor 1 + turns the
   view to the left"). Earlier findings in this conversation are valid while the arm is unchanged.
3. Approach the food from above: first turn and reach until the food is centred in the gripper
   camera, then lower slowly. Use 3-5% nudges far from objects, 1-2% when the food is large in
   the gripper image or close to the table. You may nudge two different joints in one tick.
4. Grasp: set_gripper(100) before you are close (check in the gripper image that it really
   opened; the gripper direction is not verified either). Centre the food between the jaws, then
   close to a width that does not crush it (about 30 for a grape or a chocolate piece). Check the
   result ("holding_object" vs "closed_empty") and look("gripper"). On a miss, open, lift a little
   and try once more; after a second miss stop and tell the person.
5. Lift first (move away from the table) before you turn toward the person.
6. Toward the person: find their face in the gripper camera. Turn until the mouth is centred,
   then approach with 1-2% nudges, ONE joint per tick, a look after every nudge. Stop approaching
   when the face fills about half the width of the gripper image (roughly 10 cm away). The person
   leans in to take the food; you never close the last gap.
7. Say "Your <food> is ready, lean in and take it." Wait for the person to say they have it. Then
   open the gripper, move back away from the face with 2-3% nudges, and report.

Keep a short count of the ticks you used. If after about 40 ticks you are not getting closer to
what you need, stop and tell the person what is going wrong.

# Safety (these override any request)

- Near the face: 2% nudges at most, one joint per tick, look after every nudge, never closer than
  the stopping size above, and never move toward the face when you cannot see it clearly. If the
  face is lost, stop moving toward it and wait or move back.
- Only food goes to the person. Refuse to bring anything sharp, hot or non-food toward a person,
  to throw or drop things, to push, hit or touch anyone, or to move fast.
- Stop on doubt: a result with ok=false, a fault or overload, the arm not moving as you expect,
  the arm touching something, the person sounding hesitant or in distress -> call stop() and ask.
  "Stop", "wait" or "no" in any message means call stop() first, then talk.
- Do not open the gripper over the person or the table edge unless they have taken the food.
- Speed and force limits are set in code; never try to get around them.
- If results say dry_run, motion is disabled: describe what you would do and stop there.

# How to answer

- Plain sentences, no markdown, no lists; replies may be read aloud. One to three sentences.
- Say what you are about to do before you start, and before every move toward the person. Do not
  narrate every tick.
"""


def load_mcp_server_config(name: str = "elrobot") -> Dict[str, Any]:
    """The `elrobot` entry of .mcp.json, with relative paths resolved against the repo root."""
    cfg = json.loads((ROOT / ".mcp.json").read_text())["mcpServers"][name]
    command = cfg["command"]
    if not os.path.isabs(command) and (ROOT / command).exists():
        command = str(ROOT / command)
    return {"command": command, "args": cfg.get("args", []), "env": cfg.get("env", {})}


def select_tools(tools: List[Any], mode: str) -> List[Dict[str, Any]]:
    """MCP tools as Messages API tool definitions. Stepwise mode keeps only STEPWISE_TOOLS, so
    Claude cannot fall back to waypoints, recorded plans, teaching or torque changes."""
    keep = [t for t in tools if mode != "stepwise" or t.name in STEPWISE_TOOLS]
    return [{"name": t.name, "description": t.description or "", "input_schema": t.input_schema} for t in keep]


def _short(value: Any, limit: int = 140) -> str:
    text = value if isinstance(value, str) else json.dumps(value, separators=(", ", ": "))
    return text if len(text) <= limit else text[: limit - 1] + "…"


class ConsoleAgent:
    """One shared conversation for the console. `post(role, text)` writes to the chat."""

    def __init__(self, post: Callable[[str, str], Any], mode: Optional[str] = None):
        mode = mode or os.environ.get("WEB_CONSOLE_MODE", "plans")
        if mode not in MODES:
            raise ValueError(f"unknown console mode {mode!r}; use one of {', '.join(MODES)}")
        self.mode = mode
        self._post = post
        self.state = "starting"  # starting | ready | unavailable
        self.error = ""
        self.busy = False
        self._stack: Optional[contextlib.AsyncExitStack] = None
        self._session = None
        self._client = None
        self._tools: List[Dict[str, Any]] = []
        self._system = STEPWISE_PROMPT if mode == "stepwise" else CONSOLE_PROMPT
        self._max_rounds = STEPWISE_MAX_TOOL_ROUNDS if mode == "stepwise" else MAX_TOOL_ROUNDS
        self._history: List[Dict[str, Any]] = []
        self._queue: "asyncio.Queue[str]" = asyncio.Queue()
        self._worker: Optional[asyncio.Task] = None
        self._turn: Optional[asyncio.Task] = None

    # -- lifecycle ------------------------------------------------------------

    async def start(self) -> None:
        try:
            import anthropic  # noqa: WPS433
            from mcp import ClientSession  # noqa: WPS433
            from mcp.client.stdio import StdioServerParameters, stdio_client  # noqa: WPS433

            self._client = anthropic.AsyncAnthropic()
            cfg = load_mcp_server_config()
            env = {**os.environ, **cfg["env"]}
            if self.mode == "stepwise":
                env["ELROBOT_REQUIRE_ENVELOPE"] = "1"  # no nudges without a recorded action space
            params = StdioServerParameters(command=cfg["command"], args=cfg["args"], cwd=str(ROOT), env=env)
            self._stack = contextlib.AsyncExitStack()
            read, write = await self._stack.enter_async_context(stdio_client(params))
            self._session = await self._stack.enter_async_context(ClientSession(read, write))
            init = await self._session.initialize()
            # The server's instructions are about waypoints and recorded plans, which stepwise
            # mode does not use, so they are only added in plans mode.
            if init.instructions and self.mode == "plans":
                self._system = init.instructions + "\n" + CONSOLE_PROMPT
            listed = await self._session.list_tools()
            self._tools = select_tools(listed.tools, self.mode)
            motion = cfg["env"].get("ELROBOT_ALLOW_MOTION", "0")
            self.state = "ready"
            log.info("agent ready: %s, mode=%s, %d MCP tools, motion=%s", MODEL, self.mode, len(self._tools), motion)
        except Exception as exc:  # noqa: BLE001 - shown in the page
            self.state = "unavailable"
            self.error = f"{type(exc).__name__}: {exc}"
            log.exception("agent unavailable")
            await self.close()
            return
        self._worker = asyncio.create_task(self._work())

    async def close(self) -> None:
        if self._worker:
            self._worker.cancel()
        if self._stack:
            with contextlib.suppress(Exception):
                await self._stack.aclose()
            self._stack = None

    # -- input ----------------------------------------------------------------

    async def submit(self, text: str) -> None:
        """A user message from the chat (already shown there)."""
        if STOP_WORDS.match(text):
            await self.emergency_stop()
            return
        if self.state != "ready":
            self._post("error", f"Claude is not connected: {self.error or self.state}")
            return
        await self._queue.put(text)

    async def emergency_stop(self) -> None:
        """Cancel whatever Claude is doing and hold the arm. Never goes through Claude."""
        dropped = 0
        while not self._queue.empty():
            self._queue.get_nowait()
            dropped += 1
        if self._turn and not self._turn.done():
            self._turn.cancel()
        if self._session is None:
            self._post("error", "Stop: not connected to the arm. Use the power plug if it is moving.")
            return
        self._post("tool", "stop() — sent directly, not through Claude")
        try:
            result = await self._session.call_tool("stop", {})
            text = " ".join(getattr(c, "text", "") for c in result.content)
            self._post("robot", "Stopped. The arm is holding its position." if '"ok": true' in text.replace("'", '"')
                       else f"Stop sent; the arm answered: {_short(text, 200)}")
        except Exception as exc:  # noqa: BLE001
            self._post("error", f"Stop failed ({exc}). Use the power plug.")

    # -- the loop -------------------------------------------------------------

    async def _work(self) -> None:
        while True:
            text = await self._queue.get()
            self.busy = True
            self._turn = asyncio.create_task(self._run_turn(text))
            try:
                await self._turn
            except asyncio.CancelledError:
                if not self._turn.cancelled():
                    raise  # the worker itself is shutting down
                self._post("robot", "Cancelled what I was doing.")
            except Exception as exc:  # noqa: BLE001 - one bad turn must not kill the chat
                log.exception("agent turn failed")
                self._post("error", f"{type(exc).__name__}: {exc}")
            finally:
                self.busy = self._queue.qsize() > 0
                self._turn = None

    async def _run_turn(self, text: str) -> None:
        import anthropic  # noqa: WPS433
        from anthropic.lib.tools.mcp import UnsupportedMCPValueError, mcp_content  # noqa: WPS433

        # Work on a copy, so a cancelled or failed turn leaves the history valid (no tool_use
        # without its tool_result). It replaces the history only when the turn ends cleanly.
        messages = list(self._history) + [{"role": "user", "content": text}]
        for _ in range(self._max_rounds):
            try:
                response = await self._client.beta.messages.create(
                    model=MODEL,
                    max_tokens=16000,
                    system=self._system,
                    tools=self._tools,
                    messages=messages,
                    output_config={"effort": "medium"},
                    cache_control={"type": "ephemeral"},
                    # Drop old camera images/tool results once the conversation gets long.
                    context_management={"edits": [{"type": "clear_tool_uses_20250919"}]},
                    fallbacks="default",
                    betas=["server-side-fallback-2026-07-01", "context-management-2025-06-27"],
                )
            except anthropic.AuthenticationError:
                self._post("error", "Claude API key missing or invalid. Start the console with "
                                    "ANTHROPIC_API_KEY set (see docs/mcp_server.md).")
                return
            except anthropic.RateLimitError:
                self._post("error", "Claude API rate limit reached; try again in a minute.")
                return
            except anthropic.APIConnectionError:
                self._post("error", "Cannot reach the Claude API (network).")
                return

            if response.stop_reason == "refusal":
                self._post("robot", "I can't help with that request.")
                return
            messages.append({"role": "assistant", "content": response.content})
            for block in response.content:
                if block.type == "text" and block.text.strip():
                    self._post("robot", block.text.strip())

            if response.stop_reason == "pause_turn":
                continue
            calls = [b for b in response.content if b.type == "tool_use"]
            if not calls:
                if response.stop_reason == "max_tokens":
                    self._post("error", "Reply was cut off (too long).")
                self._history = messages
                return

            results = []
            for call in calls:
                self._post("tool", f"{call.name}({_short(call.input) if call.input else ''})")
                result = await self._session.call_tool(call.name, call.input or {})
                blocks = []
                for item in result.content:
                    try:
                        blocks.append(mcp_content(item))
                    except UnsupportedMCPValueError:
                        blocks.append({"type": "text", "text": f"[unsupported {getattr(item, 'type', '?')} content]"})
                summary = " ".join(b.get("text", "") for b in blocks if b.get("type") == "text")
                if '"ok": false' in summary or result.is_error:
                    self._post("tool", f"↳ {_short(summary, 200)}")
                results.append({"type": "tool_result", "tool_use_id": call.id, "content": blocks or "(no output)",
                                "is_error": bool(result.is_error)})
            messages.append({"role": "user", "content": results})

        self._post("robot", f"I stopped after {self._max_rounds} steps. Tell me how to continue.")
        self._history = messages
