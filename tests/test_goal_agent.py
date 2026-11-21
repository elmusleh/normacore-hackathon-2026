"""GoalAgent loop with a fake Claude client and a fake MCP session (no network, no arm)."""

import asyncio
import json
import sys
from pathlib import Path
from types import SimpleNamespace as NS

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

pytest.importorskip("anthropic")
from mcp.types import ImageContent, TextContent  # noqa: E402

import goal_agent  # noqa: E402
from goal_agent import GoalAgent  # noqa: E402

USAGE = NS(input_tokens=10, output_tokens=5)


def tool_use(tool, **inp):
    return NS(stop_reason="tool_use", usage=USAGE,
              content=[NS(type="tool_use", name=tool, input=inp, id="t1")])


class FakeClaude:
    """Answers by call kind: vision (image, no tools), planning (tools), check (output format)."""

    def __init__(self, plans, checks=(), vision_delay=0.0):
        self.plans, self.checks = list(plans), list(checks)
        self.vision_delay = vision_delay
        self.requests = {"vision": [], "planung": [], "pruefung": []}
        self.beta = NS(messages=NS(create=self.create))

    async def create(self, **kwargs):
        if "tools" in kwargs:
            self.requests["planung"].append(kwargs)
            return self.plans.pop(0)
        if "format" in kwargs.get("output_config", {}):
            self.requests["pruefung"].append(kwargs)
            erreicht, why = self.checks.pop(0)
            return NS(stop_reason="end_turn", usage=USAGE,
                      content=[NS(type="text", text=json.dumps({"erreicht": erreicht, "begruendung": why}))])
        self.requests["vision"].append(kwargs)
        if self.vision_delay:
            await asyncio.sleep(self.vision_delay)
        return NS(stop_reason="end_turn", usage=USAGE,
                  content=[NS(type="text", text="A grape lies left of the gripper. The gripper is open.")])


def _text(data):
    return NS(content=[TextContent(type="text", text=json.dumps(data))], is_error=False)


class FakeSession:
    def __init__(self, motion_result=None, gripper_image=True):
        self.calls = []
        self.motion_result = motion_result or {"ok": True}
        self.gripper_image = gripper_image

    async def call_tool(self, name, arguments=None):
        self.calls.append((name, arguments))
        if name == "list_cameras":
            return _text({"ok": True, "cameras": [{"name": "table", "queue": "usbvideo/a"},
                                                  {"name": "gripper", "queue": "usbvideo/b"}]})
        if name == "look":
            meta = {"ok": True, "age_seconds": 0.1}
            if arguments["camera"] == "gripper" and not self.gripper_image:
                return _text({"ok": False, "error": "camera 'gripper' is not plugged in"})
            return NS(content=[TextContent(type="text", text=json.dumps(meta)),
                               ImageContent(type="image", data="ZmFrZQ==", mimeType="image/jpeg")], is_error=False)
        if name == "get_robot_state":
            return _text({"ok": True, "motion_allowed": True, "joints": {"1": {"percent_of_range": 49}}})
        if name == "list_waypoints":
            return _text({"ok": True, "waypoints": ["clear", "grape_hover"]})
        if name == "stop":
            return _text({"ok": True})
        return _text(self.motion_result)

    def motion_calls(self):
        return [c for c in self.calls if c[0] in goal_agent.MOTION_TOOLS]


MCP_TOOLS = [{"name": n, "description": n, "input_schema": {"type": "object", "properties": {"x": {"type": "number"}},
                                                             "required": []}}
             for n in ("get_robot_state", "look", "list_cameras", "list_waypoints", "go_to_waypoint",
                       "nudge_joint", "set_gripper", "enable_torque", "stop", "teach_waypoint")]


def make_agent(claude, session=None):
    posts = []
    agent = GoalAgent(lambda role, t: posts.append((role, t)))
    agent._client, agent._session, agent.state = claude, session or FakeSession(), "ready"
    agent._tools = MCP_TOOLS
    agent._setup_tools()
    return agent, posts


def texts(posts):
    return " | ".join(t for _, t in posts)


def test_planner_tools_add_begruendung_and_leave_out_stop_and_teach():
    agent, _ = make_agent(FakeClaude([]))
    names = [t["name"] for t in agent._planner_tools]
    assert names == ["go_to_waypoint", "nudge_joint", "set_gripper", "enable_torque",
                     "ziel_erreicht", "aufgeben", "frage_stellen"]
    for tool in agent._planner_tools:
        assert "begruendung" in tool["input_schema"]["required"]


def test_goal_reached_and_confirmed():
    claude = FakeClaude([tool_use("ziel_erreicht", begruendung="The grape is in the box.")],
                        checks=[(True, "Grape visible in the box.")])
    agent, posts = make_agent(claude)
    asyncio.run(agent._run_turn("Leg die Traube in die Box"))
    assert "Ziel erreicht. Prüfung: Grape visible in the box." in texts(posts)
    assert len(claude.requests["vision"]) == 2  # one call per camera
    assert claude.requests["planung"][0]["tool_choice"] == {"type": "auto", "disable_parallel_tool_use": True}
    assert "Tokens: vision 20 ein" in texts(posts)


def test_checker_says_no_and_the_loop_continues():
    claude = FakeClaude([tool_use("ziel_erreicht", begruendung="done"),
                         tool_use("aufgeben", begruendung="Box waypoint missing.")],
                        checks=[(False, "The box is still empty.")])
    agent, posts = make_agent(claude)
    asyncio.run(agent._run_turn("Leg die Traube in die Box"))
    assert "ACHTUNG" in texts(posts) and "Ziel aufgegeben" in texts(posts)
    second = claude.requests["planung"][1]["messages"][0]["content"]
    assert "The box is still empty." in second  # the checker's reason reaches the planner


def test_max_iterations(monkeypatch):
    monkeypatch.setattr(goal_agent, "MAX_ITERATIONS", 3)
    claude = FakeClaude([tool_use("nudge_joint", motor=1, delta_percent=2, begruendung="align")] * 3)
    session = FakeSession()
    agent, posts = make_agent(claude, session)
    asyncio.run(agent._run_turn("Dreh die Basis"))
    assert "3 Schritte ohne Ergebnis" in texts(posts)
    # begruendung is stripped before the MCP call
    assert session.motion_calls() == [("nudge_joint", {"motor": 1, "delta_percent": 2})] * 3


def test_question_pauses_and_the_answer_continues_the_goal():
    claude = FakeClaude([tool_use("frage_stellen", begruendung="two bowls", frage="Welche Schale, links oder rechts?"),
                         tool_use("ziel_erreicht", begruendung="done")],
                        checks=[(True, "ok")])
    agent, posts = make_agent(claude)
    asyncio.run(agent._run_turn("Bring mir die Schale"))
    assert ("robot", "Welche Schale, links oder rechts?") in posts
    assert agent._pending is not None and "Ziel erreicht" not in texts(posts)
    asyncio.run(agent._run_turn("die linke"))
    assert agent._pending is None and "Ziel erreicht" in texts(posts)
    assert "antwort_bediener" in claude.requests["planung"][1]["messages"][0]["content"]
    assert agent._pending is None


def test_dry_run_ends_the_goal_with_a_hint():
    claude = FakeClaude([tool_use("go_to_waypoint", name="grape_hover", begruendung="go")])
    session = FakeSession(motion_result={"ok": True, "legs": [{"dry_run": True, "plan": {}}]})
    agent, posts = make_agent(claude, session)
    asyncio.run(agent._run_turn("Fahr zur Traube"))
    assert "Bewegungen sind ausgeschaltet" in texts(posts) and "ELROBOT_ALLOW_MOTION" in texts(posts)
    assert len(claude.requests["planung"]) == 1


def test_stop_during_camera_description_cancels_and_holds():
    claude = FakeClaude([], vision_delay=5)
    session = FakeSession()
    agent, posts = make_agent(claude, session)

    async def go():
        agent._worker = asyncio.create_task(agent._work())
        await agent.submit("Leg die Traube in die Box")
        await asyncio.sleep(0.1)  # now inside the vision calls
        await agent.submit("stop")
        await asyncio.sleep(0.05)
        agent._worker.cancel()

    asyncio.run(go())
    assert ("stop", {}) in session.calls
    assert claude.requests["planung"] == []
    assert ("robot", "Cancelled what I was doing.") in posts


def test_new_goal_cancels_the_running_one():
    claude = FakeClaude([tool_use("aufgeben", begruendung="no box")], vision_delay=0.2)
    session = FakeSession()
    agent, posts = make_agent(claude, session)

    async def go():
        agent._worker = asyncio.create_task(agent._work())
        await agent.submit("erstes Ziel")
        await asyncio.sleep(0.05)
        await agent.submit("zweites Ziel")
        await asyncio.sleep(0.6)
        agent._worker.cancel()

    asyncio.run(go())
    assert "das laufende Ziel wird abgebrochen" in texts(posts)
    assert ("stop", {}) in session.calls
    assert "Ziel: zweites Ziel" in texts(posts) and "Ziel aufgegeben" in texts(posts)


def test_camera_without_picture_is_described_not_fatal():
    claude = FakeClaude([tool_use("aufgeben", begruendung="gripper camera missing")])
    agent, posts = make_agent(claude, FakeSession(gripper_image=False))
    asyncio.run(agent._run_turn("Schau in den Greifer"))
    plan_input = claude.requests["planung"][0]["messages"][0]["content"]
    assert "Kein Bild: camera 'gripper' is not plugged in" in plan_input
    assert len(claude.requests["vision"]) == 1


def test_robot_object_has_every_field():
    agent, _ = make_agent(FakeClaude([]))
    run = goal_agent.GoalRun(goal="x", iteration=2, last_action={"werkzeug": "nudge_joint"})
    robot = asyncio.run(agent._robot_object(run, {"table": "empty table"}))
    assert set(robot) >= {"goal", "state", "waypoints", "config", "motion_allowed", "cameras",
                          "iteration", "max_iterations", "last_action"}
    assert set(robot["config"]) == set(goal_agent.CONFIG_KEYS)
    assert robot["cameras"] == {"table": "empty table"} and robot["motion_allowed"] is True


def test_api_error_ends_the_goal():
    import anthropic

    class Broken(FakeClaude):
        async def create(self, **kwargs):
            if "tools" in kwargs:
                raise anthropic.APIConnectionError(request=NS(method="POST", url="x"))
            return await super().create(**kwargs)

    agent, posts = make_agent(Broken([]))
    asyncio.run(agent._run_turn("irgendwas"))
    assert ("error", "Abgebrochen wegen eines Fehlers. Claude-API nicht erreichbar (Netzwerk).") in posts
