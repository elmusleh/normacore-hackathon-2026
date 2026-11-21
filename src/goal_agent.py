"""Goal agent behind the web console: pursues one goal in a fixed loop until it is reached.

A chat message (not a stop word) is a goal, e.g. "put a grape in the box". Per iteration:

  1. Every live camera is fetched with the MCP `look` tool and described in text by its own
     Claude vision call (in parallel). The goal goes with each call, so the description
     focuses on what matters for it.
  2. One object `robot` holds everything for planning: joint state, waypoints, the relevant
     config, motion_allowed, the camera descriptions, iteration counters and the last action.
  3. A planning call sees the goal, `robot` and a compact history (text only, no images) and
     calls exactly one tool: a motion tool of the MCP server, ziel_erreicht, aufgeben or
     frage_stellen.
  4. The tool runs through the MCP server (all its limits apply). A dry_run result (motion is
     disabled in .mcp.json) ends the goal at once.
  5. ziel_erreicht is only accepted after an independent check: fresh pictures of every
     camera plus the goal, answered yes/no by a separate call.

The goal ends when it is reached and confirmed, on aufgeben, after MAX_ITERATIONS, on a stop
word or the Stop button, on a new goal, on an API error, or on dry_run. frage_stellen pauses
it: the next chat message is the answer and the same goal continues.

Stop words, the Stop button, the MCP session and the chat worker come from ConsoleAgent.

Environment (defaults in brackets):
  GOAL_AGENT_MAX_ITERATIONS [20]      GOAL_AGENT_MAX_TOKENS [16000]
  GOAL_AGENT_HISTORY_FULL [4]         steps kept in full in the planner's history
  GOAL_AGENT_VISION_MODEL / _PLAN_MODEL / _CHECK_MODEL   [WEB_CONSOLE_MODEL, claude-opus-5-5]
  GOAL_AGENT_VISION_EFFORT [low]      GOAL_AGENT_PLAN_EFFORT [medium]   GOAL_AGENT_CHECK_EFFORT [medium]
"""

from __future__ import annotations

import asyncio
import copy
import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from console_agent import MODEL, STOP_WORDS, ConsoleAgent, _short
from elrobot_config import load_config
from elrobot_log import LOG_DIR

log = logging.getLogger("elrobot.console.goal")


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


MAX_ITERATIONS = _env_int("GOAL_AGENT_MAX_ITERATIONS", 20)
MAX_TOKENS = _env_int("GOAL_AGENT_MAX_TOKENS", 16000)
HISTORY_FULL = _env_int("GOAL_AGENT_HISTORY_FULL", 4)
VISION_MODEL = os.environ.get("GOAL_AGENT_VISION_MODEL") or MODEL
PLAN_MODEL = os.environ.get("GOAL_AGENT_PLAN_MODEL") or MODEL
CHECK_MODEL = os.environ.get("GOAL_AGENT_CHECK_MODEL") or MODEL
VISION_EFFORT = os.environ.get("GOAL_AGENT_VISION_EFFORT", "low")
PLAN_EFFORT = os.environ.get("GOAL_AGENT_PLAN_EFFORT", "medium")
CHECK_EFFORT = os.environ.get("GOAL_AGENT_CHECK_EFFORT", "medium")
MAX_FRAME_AGE_S = 2.0
BETAS = ["server-side-fallback-2026-07-01"]

# Motion tools of the MCP server the planner may call. Not teach_waypoint, not stop.
MOTION_TOOLS = ("go_to_waypoint", "nudge_joint", "set_gripper", "enable_torque")
CONFIG_KEYS = ("joint_map", "gripper", "agent", "workspace", "cameras")

VISION_PROMPT = """\
You describe one camera picture for a robot arm controller that cannot see the picture itself.
The setup: an ElRobot arm (7 joints and a parallel gripper) at a table, used as an assistive
feeding robot. Cameras: "table" looks at the table from above, "gripper" sits on the gripper,
others may show a side view.

Describe in plain sentences, factual and specific:
- which objects are where (relative to the arm, the gripper and the table edges; left/right as
  seen in this picture, and say so);
- where the gripper is and whether it is open, closed, or holding something;
- obstacles, people or hands in the work area;
- anything relevant to the goal, and what you cannot tell from this picture.
Do not plan or suggest moves. No markdown. At most 120 words."""

PLAN_PROMPT = """\
You control an ElRobot arm (7 joints + gripper) at a table, through tools, step by step, to reach
the goal given by the operator. You cannot see the cameras: each step you get a JSON object
`robot` with the joint state, taught waypoints, the relevant config, whether motion is allowed,
a text description per camera (written for you this step), and your last action with its result.

Each step, call exactly ONE tool. Put one sentence into its `begruendung`: what the camera
descriptions and the state show, and why this step. Write it in the operator's language.

Moving:
- You can only reach taught waypoints (go_to_waypoint) or nudge one joint by up to 5 % of its
  range (nudge_joint). You cannot move to x/y/z points. "<place>_hover" is above "<place>",
  "clear" is a safe pose above the table. Use via_clear=false only for a short hop between nearby
  poses (hover -> grasp and back).
- If torque is off on the motors you need, call enable_torque first.
- set_gripper: 100 = open, 0 = closed; about 30 for a grape; never squeeze soft food fully.

Deciding:
- Call ziel_erreicht only when the camera descriptions show that the goal is done. An
  independent check with fresh pictures follows; if it disagrees, you get its reason as the
  last action and continue.
- Call frage_stellen if the goal could mean two different things, before moving.
- Call aufgeben if a needed waypoint is missing (say which, the operator can teach it), if an
  object you need is in no camera description, if a camera you need failed, or if the same
  action failed twice.
- Do not repeat a failed move unchanged. After a refused or failed move, re-plan.
- Do not move toward a person's face except to a taught "serve" pose."""

CHECK_PROMPT = """\
You are an independent checker for a robot arm. You get the operator's goal and fresh pictures
from every camera. Decide only from the pictures whether the goal is reached now. If the
pictures do not show it clearly, answer erreicht=false and say what is missing."""

CHECK_SCHEMA = {
    "type": "object",
    "properties": {"erreicht": {"type": "boolean"}, "begruendung": {"type": "string"}},
    "required": ["erreicht", "begruendung"],
    "additionalProperties": False,
}

OWN_TOOLS = [
    {"name": "ziel_erreicht", "strict": True,
     "description": "The goal is reached, as the camera descriptions show. Triggers an independent "
                    "check with fresh pictures before the goal ends.",
     "input_schema": {"type": "object", "additionalProperties": False, "required": ["begruendung"],
                      "properties": {"begruendung": {"type": "string"}}}},
    {"name": "aufgeben", "strict": True,
     "description": "Stop pursuing the goal: it cannot be reached with the taught waypoints, a needed "
                    "object or camera is missing, or the same action failed twice. Say what is needed.",
     "input_schema": {"type": "object", "additionalProperties": False, "required": ["begruendung"],
                      "properties": {"begruendung": {"type": "string"}}}},
    {"name": "frage_stellen", "strict": True,
     "description": "Ask the operator one short question when the goal is ambiguous. The goal pauses "
                    "until the answer arrives, then continues.",
     "input_schema": {"type": "object", "additionalProperties": False, "required": ["begruendung", "frage"],
                      "properties": {"begruendung": {"type": "string"}, "frage": {"type": "string"}}}},
]


class GoalAbort(Exception):
    """Ends the current goal with a message for the chat (API errors, refusals)."""


@dataclass
class GoalRun:
    goal: str
    iteration: int = 0
    history: List[Dict[str, Any]] = field(default_factory=list)
    last_action: Optional[Dict[str, Any]] = None
    tokens: Dict[str, List[int]] = field(
        default_factory=lambda: {"vision": [0, 0], "planung": [0, 0], "pruefung": [0, 0]})

    def count(self, kind: str, usage) -> None:
        if usage is not None:
            self.tokens[kind][0] += getattr(usage, "input_tokens", 0) or 0
            self.tokens[kind][1] += getattr(usage, "output_tokens", 0) or 0

    def token_summary(self) -> str:
        return ", ".join(f"{k} {i} ein / {o} aus" for k, (i, o) in self.tokens.items())


def _planner_tool(mcp_tool: Dict[str, Any]) -> Dict[str, Any]:
    """An MCP motion tool with an extra required `begruendung`, stripped before the MCP call."""
    schema = copy.deepcopy(mcp_tool.get("input_schema") or {"type": "object", "properties": {}})
    schema.setdefault("properties", {})["begruendung"] = {
        "type": "string", "description": "One sentence: what you see and why this step."}
    schema["required"] = ["begruendung"] + [r for r in schema.get("required", []) if r != "begruendung"]
    return {"name": mcp_tool["name"], "description": mcp_tool.get("description", ""), "input_schema": schema}


def _find_dry_run(value: Any) -> bool:
    if isinstance(value, dict):
        return value.get("dry_run") is True or any(_find_dry_run(v) for v in value.values())
    if isinstance(value, list):
        return any(_find_dry_run(v) for v in value)
    return False


def _first_sentences(text: str, limit: int = 220) -> str:
    """One or two sentences for the chat; the full text goes to the log."""
    parts = text.replace("\n", " ").split(". ")
    short = ". ".join(parts[:2]).strip()
    if len(parts) > 2 and not short.endswith("."):
        short += "."
    return _short(short, limit)


class GoalAgent(ConsoleAgent):
    """Same interface as ConsoleAgent (start, submit, emergency_stop, close)."""

    def __init__(self, post: Callable[[str, str], Any]):
        super().__init__(post)
        self._pending: Optional[GoalRun] = None  # a goal waiting for the answer to frage_stellen
        self._planner_tools: List[Dict[str, Any]] = []
        self._log_path = None

    # -- lifecycle ------------------------------------------------------------

    async def start(self) -> None:
        await super().start()
        if self.state == "ready":
            self._setup_tools()
            self._setup_log()

    def _setup_tools(self) -> None:
        by_name = {t["name"]: t for t in self._tools}
        missing = [n for n in MOTION_TOOLS if n not in by_name]
        if missing:
            log.warning("MCP server lacks motion tools %s", missing)
        self._planner_tools = [_planner_tool(by_name[n]) for n in MOTION_TOOLS if n in by_name] + OWN_TOOLS

    def _setup_log(self) -> None:
        """Full camera descriptions and robot objects go to logs/goal-<time>.log, not the chat."""
        try:
            LOG_DIR.mkdir(parents=True, exist_ok=True)
            self._log_path = LOG_DIR / f"goal-{time.strftime('%Y%m%d-%H%M%S')}.log"
            handler = logging.FileHandler(self._log_path, encoding="utf-8")
            handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
            log.addHandler(handler)
            log.setLevel(logging.DEBUG)
        except OSError:
            log.warning("cannot write the goal log in %s", LOG_DIR, exc_info=True)

    # -- input ----------------------------------------------------------------

    async def submit(self, text: str) -> None:
        if STOP_WORDS.match(text):
            await self.emergency_stop()
            return
        if self.state != "ready":
            self._post("error", f"Claude is not connected: {self.error or self.state}")
            return
        if self._turn is not None and not self._turn.done():
            self._post("robot", "Neues Ziel erhalten: das laufende Ziel wird abgebrochen.")
            self._pending = None
            self._turn.cancel()
            await self._hold()
        await self._queue.put(text)

    async def emergency_stop(self) -> None:
        """Stop button or stop word: also forget a goal that waits for an answer."""
        self._pending = None
        await super().emergency_stop()

    async def _hold(self) -> None:
        """Hold the arm after cancelling a goal (a move may have been running)."""
        if self._session is None:
            return
        try:
            await self._session.call_tool("stop", {})
        except Exception:  # noqa: BLE001 - best effort; the emergency stop path reports failures
            log.exception("stop after cancel failed")

    # -- one goal -------------------------------------------------------------

    async def _run_turn(self, text: str) -> None:
        if self._pending is not None:
            run, self._pending = self._pending, None
            run.history.append({"schritt": run.iteration, "antwort_bediener": text})
            run.last_action = {"werkzeug": "frage_stellen", "ergebnis": {"antwort_bediener": text}}
            self._post("robot", f"Weiter mit dem Ziel: {run.goal}")
        else:
            run = GoalRun(goal=text)
            self._post("robot", f"Ziel: {text} (höchstens {MAX_ITERATIONS} Schritte)")
        log.info("goal %r, iteration %d", run.goal, run.iteration)
        try:
            outcome, detail = await self._pursue(run)
        except GoalAbort as exc:
            outcome, detail = "fehler", str(exc)
        if outcome == "frage":
            return  # paused; the summary comes when the goal really ends
        self._finish(run, outcome, detail)

    def _finish(self, run: GoalRun, outcome: str, detail: str) -> None:
        headline = {
            "erreicht": "Ziel erreicht",
            "aufgegeben": "Ziel aufgegeben",
            "max_iterations": f"Abgebrochen: {MAX_ITERATIONS} Schritte ohne Ergebnis",
            "dry_run": "Abgebrochen: Bewegungen sind ausgeschaltet",
            "fehler": "Abgebrochen wegen eines Fehlers",
        }.get(outcome, outcome)
        role = "error" if outcome == "fehler" else "robot"
        self._post(role, f"{headline}. {detail}".strip())
        self._post("tool", f"Schritte: {run.iteration}/{MAX_ITERATIONS}. Tokens: {run.token_summary()}")
        log.info("goal %r ended: %s (%s); %s", run.goal, outcome, detail, run.token_summary())

    async def _pursue(self, run: GoalRun) -> Tuple[str, str]:
        while run.iteration < MAX_ITERATIONS:
            run.iteration += 1
            self._post("tool", f"Schritt {run.iteration}/{MAX_ITERATIONS}")
            cameras = await self._describe_cameras(run)
            for name, desc in cameras.items():
                self._post("tool", f"{name}: {_first_sentences(desc)}")
            robot = await self._robot_object(run, cameras)
            log.debug("step %d robot object:\n%s", run.iteration, json.dumps(robot, indent=1, default=str))

            decision = await self._plan(run, robot)
            if decision is None:
                run.last_action = {"werkzeug": None, "ergebnis": {"ok": False,
                                   "error": "Kein Werkzeug aufgerufen. Rufe genau ein Werkzeug auf."}}
                self._remember(run, cameras)
                continue
            name, args, why = decision
            if why:
                self._post("robot", why)

            if name == "aufgeben":
                return "aufgegeben", ""
            if name == "frage_stellen":
                self._post("robot", args.get("frage", "Was genau meinst du?"))
                self._pending = run
                return "frage", ""
            if name == "ziel_erreicht":
                self._post("tool", "ziel_erreicht() → unabhängige Prüfung mit neuen Bildern")
                verdict = await self._verify(run)
                if verdict["erreicht"]:
                    return "erreicht", f"Prüfung: {verdict['begruendung']}"
                self._post("error", f"ACHTUNG: Planer meldet erreicht, die Prüfung sagt nein: "
                                    f"{verdict['begruendung']}")
                run.last_action = {"werkzeug": "ziel_erreicht", "ergebnis": {
                    "bestaetigt": False, "pruefung": verdict["begruendung"]}}
                self._remember(run, cameras)
                continue

            self._post("tool", f"{name}({_short(args) if args else ''})")
            result = await self._call_tool(name, args)
            run.last_action = {"werkzeug": name, "parameter": args, "ergebnis": result}
            self._remember(run, cameras)
            if not result.get("ok", True) or result.get("error"):
                self._post("tool", f"↳ {_short(result, 200)}")
            if _find_dry_run(result):
                return "dry_run", ("Ich habe nur den Plan gezeigt. Zum Bewegen ELROBOT_ALLOW_MOTION in .mcp.json "
                                   "auf \"1\" setzen und die Konsole neu starten.")
        return "max_iterations", ""

    def _remember(self, run: GoalRun, cameras: Dict[str, str]) -> None:
        run.history.append({
            "schritt": run.iteration,
            "aktion": run.last_action,
            "kameras": {n: _first_sentences(d, 160) for n, d in cameras.items()},
        })

    def _compact_history(self, run: GoalRun) -> List[Dict[str, Any]]:
        """The last HISTORY_FULL steps in full, older ones as one line each."""
        keep = max(0, HISTORY_FULL)
        cut = len(run.history) - keep
        older, recent = run.history[:max(0, cut)], run.history[max(0, cut):]
        short = []
        for h in older:
            action = h.get("aktion") or {}
            result = action.get("ergebnis") if isinstance(action, dict) else None
            ok = result.get("ok") if isinstance(result, dict) else None
            short.append({"schritt": h.get("schritt"), "werkzeug": action.get("werkzeug") if action else None,
                          "ok": ok, **({"antwort_bediener": h["antwort_bediener"]} if "antwort_bediener" in h else {})})
        return short + recent

    # -- 1. cameras -----------------------------------------------------------

    async def _describe_cameras(self, run: GoalRun) -> Dict[str, str]:
        """Text description per live camera; failures become text, never an exception."""
        images = await self._grab_images()
        if not images:
            return {"kameras": "Keine Kamera liefert ein Bild (list_cameras ist leer)."}
        names = list(images)
        results = await asyncio.gather(*(self._describe_one(run, n, images[n]) for n in names))
        return dict(zip(names, results))

    async def _grab_images(self) -> Dict[str, Any]:
        """name -> (jpeg_base64, mime) or an error string, for every live camera."""
        listed = await self._call_tool("list_cameras", {})
        cams = listed.get("cameras") or []
        out: Dict[str, Any] = {}
        for cam in cams:
            target = cam.get("name") or cam.get("queue")
            if not target:
                continue
            label = cam.get("name") or f"{cam.get('product') or 'kamera'} ({cam.get('queue')})"
            out[label] = await self._look(target)
        return out

    async def _look(self, target: str) -> Any:
        result = await self._session.call_tool("look", {"camera": target})
        meta: Dict[str, Any] = {}
        image = None
        for item in result.content:
            if getattr(item, "type", "") == "image":
                image = (item.data, getattr(item, "mimeType", None) or "image/jpeg")
            elif getattr(item, "type", "") == "text":
                try:
                    meta = json.loads(item.text)
                except (TypeError, ValueError):
                    meta = {"ok": False, "error": item.text}
        if image is None:
            return f"Kein Bild: {meta.get('error') or 'die Kamera liefert nichts'}."
        age = meta.get("age_seconds")
        if age is not None and age > MAX_FRAME_AGE_S:
            return f"Bild ist {age:.1f} s alt: die Kamera hängt oder ist getrennt. Nicht auswerten."
        return image

    async def _describe_one(self, run: GoalRun, name: str, image: Any) -> str:
        if isinstance(image, str):
            return image
        data, mime = image
        try:
            response = await self._create("vision", run, model=VISION_MODEL, effort=VISION_EFFORT,
                                          system=VISION_PROMPT, messages=[{"role": "user", "content": [
                                              {"type": "image", "source": {"type": "base64", "media_type": mime,
                                                                           "data": data}},
                                              {"type": "text", "text": f"Camera: {name}\nGoal: {run.goal}"}]}])
        except GoalAbort as exc:
            return f"Bildauswertung fehlgeschlagen: {exc}"
        text = " ".join(b.text for b in response.content if getattr(b, "type", "") == "text").strip()
        log.info("step %d camera %s: %s", run.iteration, name, text)
        return text or "Keine Beschreibung erhalten."

    # -- 2. robot object ------------------------------------------------------

    async def _robot_object(self, run: GoalRun, cameras: Dict[str, str]) -> Dict[str, Any]:
        state = await self._call_tool("get_robot_state", {})
        waypoints = await self._call_tool("list_waypoints", {})
        cfg = load_config()
        return {
            "goal": run.goal,
            "state": state,
            "waypoints": waypoints,
            "config": {k: cfg.get(k) for k in CONFIG_KEYS},
            "motion_allowed": state.get("motion_allowed"),
            "cameras": cameras,
            "iteration": run.iteration,
            "max_iterations": MAX_ITERATIONS,
            "last_action": run.last_action,
        }

    # -- 3. plan --------------------------------------------------------------

    async def _plan(self, run: GoalRun, robot: Dict[str, Any]) -> Optional[Tuple[str, Dict[str, Any], str]]:
        content = (f"Goal: {run.goal}\n\nrobot:\n{json.dumps(robot, ensure_ascii=False, default=str)}\n\n"
                   f"History (older steps shortened):\n"
                   f"{json.dumps(self._compact_history(run), ensure_ascii=False, default=str)}\n\n"
                   "Call exactly one tool now.")
        response = await self._create("planung", run, model=PLAN_MODEL, effort=PLAN_EFFORT, system=PLAN_PROMPT,
                                      tools=self._planner_tools,
                                      tool_choice={"type": "auto", "disable_parallel_tool_use": True},
                                      messages=[{"role": "user", "content": content}])
        calls = [b for b in response.content if getattr(b, "type", "") == "tool_use"]
        if not calls:
            text = " ".join(b.text for b in response.content if getattr(b, "type", "") == "text").strip()
            if text:
                self._post("robot", text)
            log.warning("step %d: planner called no tool (%s)", run.iteration, response.stop_reason)
            return None
        call = calls[0]
        args = dict(call.input or {})
        why = str(args.pop("begruendung", "") or "")
        log.info("step %d plan: %s %s — %s", run.iteration, call.name, args, why)
        return call.name, args, why

    # -- 5. verify ------------------------------------------------------------

    async def _verify(self, run: GoalRun) -> Dict[str, Any]:
        images = await self._grab_images()
        content: List[Dict[str, Any]] = []
        for name, image in images.items():
            if isinstance(image, str):
                content.append({"type": "text", "text": f"Camera {name}: {image}"})
                continue
            data, mime = image
            content += [{"type": "text", "text": f"Camera {name}:"},
                        {"type": "image", "source": {"type": "base64", "media_type": mime, "data": data}}]
        if not any(c["type"] == "image" for c in content):
            return {"erreicht": False, "begruendung": "Keine Kamera liefert ein Bild; nicht prüfbar."}
        content.append({"type": "text", "text": f"Goal: {run.goal}\nIs the goal reached now?"})
        response = await self._create("pruefung", run, model=CHECK_MODEL, effort=CHECK_EFFORT, system=CHECK_PROMPT,
                                      messages=[{"role": "user", "content": content}],
                                      output_format=CHECK_SCHEMA)
        text = next((b.text for b in response.content if getattr(b, "type", "") == "text"), "")
        try:
            verdict = json.loads(text)
            verdict = {"erreicht": bool(verdict["erreicht"]), "begruendung": str(verdict["begruendung"])}
        except (ValueError, KeyError, TypeError):
            verdict = {"erreicht": False, "begruendung": f"Prüfung nicht lesbar: {_short(text, 120)}"}
        log.info("step %d check: %s", run.iteration, verdict)
        return verdict

    # -- helpers --------------------------------------------------------------

    async def _call_tool(self, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Run an MCP tool and return its JSON result (text content) as a dict."""
        result = await self._session.call_tool(name, args)
        texts = [getattr(c, "text", "") for c in result.content if getattr(c, "type", "") == "text"]
        try:
            data = json.loads(texts[0]) if texts else {}
        except ValueError:
            data = {"ok": False, "error": _short(" ".join(texts), 300)}
        if not isinstance(data, dict):
            data = {"ok": True, "result": data}
        if result.is_error:
            data.setdefault("ok", False)
        return data

    async def _create(self, kind: str, run: GoalRun, *, model: str, effort: str, system: str,
                      messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]] = None,
                      tool_choice: Optional[Dict[str, Any]] = None,
                      output_format: Optional[Dict[str, Any]] = None):
        """One Claude call; API errors and refusals become GoalAbort with a chat message."""
        import anthropic  # noqa: WPS433

        output_config: Dict[str, Any] = {"effort": effort}
        if output_format is not None:
            output_config["format"] = {"type": "json_schema", "schema": output_format}
        kwargs: Dict[str, Any] = dict(model=model, max_tokens=MAX_TOKENS, system=system, messages=messages,
                                      output_config=output_config, fallbacks="default", betas=BETAS)
        if tools:
            kwargs["tools"] = tools
        if tool_choice:
            kwargs["tool_choice"] = tool_choice
        try:
            response = await self._client.beta.messages.create(**kwargs)
        except anthropic.AuthenticationError:
            raise GoalAbort("Claude-API-Key fehlt oder ist ungültig (ANTHROPIC_API_KEY in .env).") from None
        except anthropic.RateLimitError:
            raise GoalAbort("Claude-API-Limit erreicht; in einer Minute noch einmal versuchen.") from None
        except anthropic.APIStatusError as exc:
            raise GoalAbort(f"Claude-API-Fehler {exc.status_code}: {_short(str(exc.message), 160)}") from None
        except anthropic.APIConnectionError:
            raise GoalAbort("Claude-API nicht erreichbar (Netzwerk).") from None
        run.count(kind, getattr(response, "usage", None))
        if response.stop_reason == "refusal":
            raise GoalAbort(f"Claude hat die Anfrage ({kind}) abgelehnt.")
        if response.stop_reason == "max_tokens":
            log.warning("%s reply cut off at max_tokens", kind)
        return response
