"""
Unified Mission Control Backend for NormaCore Tabletop Robotics.
Serves Web Dashboard (port 8080) with real-time controls for:
  - Dual live camera feeds (Table + Person) with dropdown selectors
    supporting both NormaCore Station USB queues and local V4L2 cameras
  - Live FeedingVisionDetector bounding boxes & detection event streaming
  - CLI runner integration (execute any cli.sh command directly from Web UI)
  - Master / Slave Teleop Sync toggle
  - Live hardware telemetry (Buses 5B61034962 and 5B61037051)
  - Waypoints (Home, Clear, Pick, Place)
  - Emergency E-Stop (Torque Off)
  - Automated Testing (pytest) and Judge Perturbation Recovery Demo
"""

import base64
import http.server
import io
import json
import os
import socket
import socketserver
import subprocess
import sys
import threading
import time
import urllib.parse
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

# Ensure src is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from elrobot_config import load_config, load_waypoints, save_config
from feeding_vision import FeedingVisionDetector, run_camera_feeding_cycle
from mcp_server import NormaCoreMCPServer
from vision_homography import TabletopCalibrator

SERVER_PORT = 8080
STATION_PORT = 8888
mcp_server = NormaCoreMCPServer()
calibrator = TabletopCalibrator()
feeding_detector = FeedingVisionDetector(calibrator=mcp_server.calibrator)

# Global state for teleoperation background subprocess
teleop_process: Optional[subprocess.Popen] = None
teleop_lock = threading.Lock()
latest_feeding_overlay_b64: Optional[str] = None
latest_mouth_sample: Dict[str, Any] = {"mar": None, "width_px": None, "closed_mar": None}


def _station_reachable(timeout_s: float = 0.25) -> bool:
    try:
        cfg = load_config()
        server = os.environ.get("ELROBOT_STATION", cfg["station"]["server"])
        host, _, port = server.partition(":")
        with socket.create_connection((host or "localhost", int(port or STATION_PORT)), timeout=timeout_s):
            return True
    except OSError:
        return False


class CameraHub:
    """Discovers and streams frames from Station USB queues, local V4L2 devices, or simulator."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._station_lock = threading.Lock()
        self._detect_lock = threading.Lock()
        self._station_tools = None
        self._station_hw = None
        self._v4l2_caps: Dict[int, cv2.VideoCapture] = {}
        self._v4l2_locks: Dict[int, threading.Lock] = {}
        self._cameras: List[Dict[str, Any]] = []
        self._last_scan: float = 0.0
        self.selected: Dict[str, str] = {"table": "mock:sim", "person": "mock:sim"}

    def _get_station_tools(self):
        """Lazily connect to the NormaCore Station if reachable."""
        if not _station_reachable():
            self._close_station()
            return None
        if self._station_tools is not None:
            return self._station_tools
        try:
            from elrobot_hardware import ElRobotHardwareSync
            from robot_tools import RobotTools

            cfg = load_config()
            server = os.environ.get("ELROBOT_STATION", cfg["station"]["server"])
            bus = os.environ.get("ELROBOT_BUS", cfg["station"]["bus"])
            hw = ElRobotHardwareSync(server=server, bus=bus)
            hw.connect(timeout_s=3.0)
            self._station_hw = hw
            self._station_tools = RobotTools(lambda: hw)
            return self._station_tools
        except Exception:
            self._close_station()
            return None

    def _close_station(self) -> None:
        if self._station_hw is not None:
            try:
                self._station_hw.close()
            except Exception:
                pass
        self._station_hw = None
        self._station_tools = None

    def discover(self, force: bool = False) -> List[Dict[str, Any]]:
        """Discover all live Station USB cameras and local V4L2 capture cameras."""
        now = time.time()
        with self._lock:
            if not force and self._cameras and (now - self._last_scan) < 10.0:
                return list(self._cameras)

        found: List[Dict[str, Any]] = []

        # 1. Station USB cameras (KD-USB Cameras, etc. claimed via libuvc)
        with self._station_lock:
            tools = self._get_station_tools()
            if tools is not None:
                try:
                    cam_res = tools.list_cameras()
                    for cam in cam_res.get("cameras", []):
                        if not cam.get("live", False):
                            continue
                        queue = cam["queue"]
                        port = cam.get("port") or "unknown"
                        product = cam.get("product") or "Station Camera"
                        name_tag = f" [{cam['name']}]" if cam.get("name") else ""
                        found.append({
                            "id": f"station:{queue}",
                            "type": "station",
                            "label": f"Station: {product} (port {port}){name_tag}",
                            "port": port,
                            "queue": queue,
                        })
                except Exception:
                    self._close_station()

        # 2. Local V4L2 cameras (/dev/video*)
        v4l_root = Path("/sys/class/video4linux")
        if v4l_root.is_dir():
            nodes = sorted(
                v4l_root.glob("video*"),
                key=lambda p: int(p.name.replace("video", "")) if p.name.replace("video", "").isdigit() else 999,
            )
            for node in nodes:
                idx_str = node.name.replace("video", "")
                if not idx_str.isdigit():
                    continue
                idx = int(idx_str)
                try:
                    dev_name = (node / "name").read_text().strip()
                except OSError:
                    dev_name = f"Camera {idx}"

                # Probe briefly (reusing open capture if already active)
                if self._probe_v4l2(idx):
                    found.append({
                        "id": f"v4l2:{idx}",
                        "type": "v4l2",
                        "label": f"USB/V4L2: /dev/video{idx} — {dev_name}",
                        "device": f"/dev/video{idx}",
                    })

        # 3. Always include offline simulator fallback
        found.append({
            "id": "mock:sim",
            "type": "mock",
            "label": "Offline Simulator (Mock Table)",
        })

        with self._lock:
            self._cameras = found
            self._last_scan = time.time()
            valid_ids = {c["id"] for c in found}
            real_cams = [c["id"] for c in found if c["type"] != "mock"]

            # Match configured cameras from config/elrobot.json first
            cfg_cams = load_config().get("cameras", {})

            def _resolve_cfg(role: str) -> Optional[str]:
                val = cfg_cams.get(role, "")
                if not val:
                    return None
                if val in valid_ids:
                    return val
                if val.startswith("port:"):
                    want_port = val[len("port:"):]
                    for c in found:
                        if c.get("port") == want_port:
                            return c["id"]
                return None

            # Auto-assign from config or fallback to first real cameras
            if self.selected["table"] not in valid_ids or self.selected["table"] == "mock:sim":
                self.selected["table"] = _resolve_cfg("table") or (real_cams[0] if real_cams else "mock:sim")
            if self.selected["person"] not in valid_ids or self.selected["person"] == "mock:sim":
                cfg_person = _resolve_cfg("person")
                if cfg_person:
                    self.selected["person"] = cfg_person
                elif len(real_cams) >= 2:
                    self.selected["person"] = next((c for c in real_cams if c != self.selected["table"]), real_cams[1])
                elif real_cams:
                    self.selected["person"] = real_cams[0]
                else:
                    self.selected["person"] = "mock:sim"

            return list(self._cameras)

    @staticmethod
    def _configure_v4l2_hd(cap: cv2.VideoCapture) -> None:
        """Request crisp 1280x720 MJPG from V4L2 cameras (e.g. OBSBOT Meet SE)."""
        try:
            cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        except Exception:
            pass

    def _probe_v4l2(self, idx: int) -> bool:
        lock = self._v4l2_locks.setdefault(idx, threading.Lock())
        with lock:
            cap = self._v4l2_caps.get(idx)
            if cap is not None and cap.isOpened():
                return True
            try:
                cap = cv2.VideoCapture(idx)
                if not cap.isOpened():
                    cap.release()
                    return False
                self._configure_v4l2_hd(cap)
                ret, frame = cap.read()
                if ret and frame is not None and frame.size > 0:
                    self._v4l2_caps[idx] = cap
                    return True
                cap.release()
                return False
            except Exception:
                return False

    def select_camera(self, role: str, source_id: str) -> Dict[str, str]:
        with self._lock:
            if role in self.selected:
                self.selected[role] = source_id
            return dict(self.selected)

    def save_defaults(self, table_src: Optional[str], person_src: Optional[str]) -> Dict[str, str]:
        """Persist selected Table and Person cameras to config/elrobot.json using stable port/device ids."""
        with self._lock:
            cams_by_id = {c["id"]: c for c in self._cameras}

        def _to_cfg_value(src: Optional[str]) -> Optional[str]:
            if not src or src == "mock:sim":
                return None
            info = cams_by_id.get(src)
            if info and info.get("type") == "station" and info.get("port"):
                return f"port:{info['port']}"
            return src

        cfg = load_config()
        cams = dict(cfg.get("cameras") or {})
        t_val = _to_cfg_value(table_src)
        p_val = _to_cfg_value(person_src)
        if t_val:
            cams["table"] = t_val
            self.select_camera("table", table_src)
        if p_val:
            cams["person"] = p_val
            self.select_camera("person", person_src)
        cfg["cameras"] = cams
        save_config(cfg)
        return cams

    def _read_raw_bgr(self, source_id: str) -> Tuple[Optional[np.ndarray], str]:
        if source_id.startswith("station:"):
            queue = source_id[len("station:"):]
            with self._station_lock:
                tools = self._get_station_tools()
                if tools is None:
                    return None, "Station not reachable"
                try:
                    meta, jpeg_bytes = tools.look(camera=queue)
                    if not meta.get("ok") or not jpeg_bytes:
                        return None, meta.get("error", "No frame from Station queue")
                    arr = np.frombuffer(jpeg_bytes, dtype=np.uint8)
                    frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
                    if frame is None:
                        return None, "Failed to decode Station JPEG"
                    return frame, ""
                except Exception as exc:
                    self._close_station()
                    return None, str(exc)

        if source_id.startswith("v4l2:"):
            idx = int(source_id[len("v4l2:"):])
            lock = self._v4l2_locks.setdefault(idx, threading.Lock())
            with lock:
                cap = self._v4l2_caps.get(idx)
                if cap is None or not cap.isOpened():
                    cap = cv2.VideoCapture(idx)
                    if cap.isOpened():
                        self._configure_v4l2_hd(cap)
                    self._v4l2_caps[idx] = cap
                if not cap.isOpened():
                    return None, f"Cannot open /dev/video{idx}"
                ret, frame = cap.read()
                if not ret or frame is None or frame.size == 0:
                    cap.release()
                    self._v4l2_caps.pop(idx, None)
                    return None, f"Empty frame from /dev/video{idx}"
                return frame, ""

        # Offline mock simulator
        try:
            view = mcp_server.get_calibrated_view()
            jpg_bytes = base64.b64decode(view["image_base64"])
            arr = np.frombuffer(jpg_bytes, dtype=np.uint8)
            frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            return frame, ""
        except Exception as exc:
            return None, str(exc)

    def get_annotated_frame(self, role: str = "table", source_id: Optional[str] = None) -> Dict[str, Any]:
        with self._lock:
            src = source_id or self.selected.get(role, "mock:sim")

        frame, err = self._read_raw_bgr(src)
        if frame is None:
            return {
                "ok": False,
                "role": role,
                "source": src,
                "error": err or "No frame",
                "image_base64": "",
                "detections": {},
                "summary": f"No signal ({err})",
            }

        with self._detect_lock:
            annotated_bgr = frame.copy()
            det_dict: Dict[str, Any] = {}
            parts: List[str] = []

            if role == "person":
                # Only run real face/mouth detection on the Person camera (skip fake fallback boxes)
                mouth = feeding_detector.detect_mouth(frame)
                if mouth and not (mouth.extra or {}).get("fallback", False):
                    extra = dict(mouth.extra or {})
                    u, v, w, h = mouth.u_px, mouth.v_px, mouth.width_px, mouth.height_px
                    at_standoff = bool(extra.get("at_standoff", False))
                    mouth_open = bool(extra.get("mouth_open", False))
                    confirmed = bool(extra.get("mouth_open_confirmed", False))
                    mar = extra.get("mar")
                    detector_name = extra.get("detector", "opencv")

                    color = (0, 220, 120) if not at_standoff else (0, 165, 255)
                    cv2.rectangle(annotated_bgr, (u - w // 2, v - h // 2), (u + w // 2, v + h // 2), color, 2)
                    for pt in extra.get("lip_points") or []:
                        cv2.circle(annotated_bgr, (int(pt[0]), int(pt[1])), 3, (0, 255, 255), -1)

                    mouth_tag = "OPEN!" if confirmed else ("opening" if mouth_open else "closed")
                    mar_tag = f" MAR={mar:.2f}" if mar is not None else ""
                    cv2.putText(
                        annotated_bgr,
                        f"MOUTH {mouth_tag}{mar_tag} ({extra.get('standoff_cm', '?')}cm)",
                        (max(8, u - 75), max(22, v - h // 2 - 8)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.48,
                        color,
                        2,
                    )
                    det_dict["mouth"] = {
                        "label": mouth.label,
                        "u_px": u,
                        "v_px": v,
                        "width_px": w,
                        "confidence": round(float(mouth.confidence), 2),
                        "extra": extra,
                    }
                    latest_mouth_sample["mar"] = mar
                    latest_mouth_sample["width_px"] = w
                    standoff_txt = "STOP: AT STANDOFF" if at_standoff else f"{extra.get('standoff_cm', '?')}cm (SAFE)"
                    parts.append(f"[{detector_name}] Mouth {mouth_tag}{mar_tag} — {standoff_txt}")
            else:
                # Table camera: prefer MediaPipe ObjectDetector (zero false positives on robot wires!)
                if feeding_detector._object_detector is not None:
                    mp_targets = feeding_detector.detect_table_objects(frame)
                    for idx, t in enumerate(mp_targets):
                        u, v, w, h = t.u_px, t.v_px, t.width_px, t.height_px
                        extra = dict(t.extra or {})
                        color = (180, 60, 240) if t.label == "bowl" else (50, 210, 100)
                        cv2.rectangle(annotated_bgr, (u - w // 2, v - h // 2), (u + w // 2, v + h // 2), color, 2)
                        tag = f"{t.label.upper()} ({int(t.confidence * 100)}%)"
                        if extra.get("food_piece_count"):
                            tag += f" [{extra['food_piece_count']} pcs]"
                        cv2.putText(
                            annotated_bgr,
                            tag,
                            (max(8, u - w // 2), max(22, v - h // 2 - 6)),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.5,
                            color,
                            2,
                        )
                        if extra.get("best_food_px"):
                            fu, fv, fw, fh = extra["best_food_px"]
                            cv2.circle(annotated_bgr, (fu, fv), 5, (0, 255, 255), -1)
                            cv2.rectangle(
                                annotated_bgr,
                                (fu - fw // 2, fv - fh // 2),
                                (fu + fw // 2, fv + fh // 2),
                                (0, 255, 255),
                                1,
                            )
                        det_dict[f"{t.label}_{idx}"] = {
                            "label": t.label,
                            "u_px": u,
                            "v_px": v,
                            "confidence": t.confidence,
                            "extra": extra,
                        }
                        if extra.get("food_piece_count"):
                            parts.append(f"[mediapipe] {t.label} ({int(t.confidence * 100)}%, {extra['food_piece_count']} food pcs)")
                        else:
                            parts.append(f"[mediapipe] {t.label} ({int(t.confidence * 100)}%)")
                else:
                    # Fallback if MediaPipe ObjectDetector model is missing
                    bowl = feeding_detector.detect_grape_bowl(frame)
                    if bowl and not (bowl.extra or {}).get("fallback", False):
                        u, v, w, h = bowl.u_px, bowl.v_px, bowl.width_px, bowl.height_px
                        cv2.rectangle(annotated_bgr, (u - w // 2, v - h // 2), (u + w // 2, v + h // 2), (180, 60, 240), 2)
                        cv2.putText(
                            annotated_bgr,
                            f"BOWL ({int(bowl.confidence * 100)}%)",
                            (max(8, u - 45), max(22, v - h // 2 - 8)),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.5,
                            (180, 60, 240),
                            2,
                        )
                        det_dict["grape_bowl"] = {
                            "label": bowl.label,
                            "u_px": u,
                            "v_px": v,
                            "confidence": round(float(bowl.confidence), 2),
                            "extra": dict(bowl.extra or {}),
                        }
                        parts.append(f"bowl ({int(bowl.confidence * 100)}%)")

        if parts:
            summary = ", ".join(parts)
        elif role == "person":
            summary = "Live feed (no face in frame)"
        else:
            summary = "Live feed (clean — ready for AI vision)"

        ok, buf = cv2.imencode(".jpg", annotated_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
        b64 = base64.b64encode(buf.tobytes()).decode("utf-8") if ok else ""

        return {
            "ok": True,
            "role": role,
            "source": src,
            "image_base64": b64,
            "detections": det_dict,
            "summary": summary,
        }


camera_hub = CameraHub()


def get_live_camera_feed():
    """Backwards-compatible helper returning the active table camera JPEG base64."""
    res = camera_hub.get_annotated_frame(role="table")
    if res.get("image_base64"):
        return res["image_base64"]
    if latest_feeding_overlay_b64:
        return latest_feeding_overlay_b64
    return ""


class ThreadingHTTPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True


class MissionControlHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:
        # Suppress noisy per-frame GET logs
        pass

    def _send_json(self, payload: Dict[str, Any], status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        qs = urllib.parse.parse_qs(parsed.query)

        if path in ["/", "/index.html"]:
            html_path = os.path.join(os.path.dirname(__file__), "digital_twin.html")
            with open(html_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
            return

        if path == "/api/cameras":
            force = qs.get("refresh", ["0"])[0] in ("1", "true", "yes")
            cams = camera_hub.discover(force=force)
            self._send_json({
                "cameras": cams,
                "selected": dict(camera_hub.selected),
                "station_reachable": _station_reachable(),
            })
            return

        if path == "/api/frame":
            role = qs.get("role", ["table"])[0]
            source = qs.get("source", [None])[0]
            frame_res = camera_hub.get_annotated_frame(role=role, source_id=source)
            self._send_json(frame_res)
            return

        if path == "/api/state":
            global teleop_process
            is_teleop_running = teleop_process is not None and teleop_process.poll() is None

            station = mcp_server.station
            telemetry = station.get_arm_telemetry()

            st_cfg = load_config().get("station", {})
            payload = {
                "teleop_active": is_teleop_running,
                "station_reachable": _station_reachable(),
                "master_bus": st_cfg.get("leader_bus", "5B61037051"),
                "slave_bus": st_cfg.get("bus", "5B61034962"),
                "arm_pose": telemetry["end_effector"],
                "gripper_state": telemetry["gripper_state"],
                "gripper_load": telemetry["gripper_load"],
                "held_object": telemetry["held_object"],
                "objects": getattr(station, "objects", {}),
                "target_zones": getattr(station, "target_zones", {}),
                "selected_cameras": dict(camera_hub.selected),
                "waypoints": sorted(load_waypoints().keys()),
                "feeding_calibration": feeding_detector.get_calibration(),
                "latest_mouth_sample": dict(latest_mouth_sample),
            }
            self._send_json(payload)
            return

        super().do_GET()

    def do_POST(self):
        global teleop_process, latest_feeding_overlay_b64
        if self.path == "/api/command":
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length)
            try:
                cmd = json.loads(post_data.decode("utf-8"))
                action = cmd.get("action")
                res: Dict[str, Any] = {"status": "SUCCESS"}

                if action == "select_camera":
                    role = cmd.get("role", "table")
                    source = cmd.get("source", "mock:sim")
                    selected = camera_hub.select_camera(role, source)
                    res = {"status": "CAMERA_UPDATED", "selected": selected}

                elif action == "save_camera_defaults":
                    saved = camera_hub.save_defaults(cmd.get("table"), cmd.get("person"))
                    res = {
                        "status": "CAMERA_DEFAULTS_SAVED",
                        "cameras": saved,
                        "output": f"Saved defaults to config/elrobot.json: table={saved.get('table')}, person={saved.get('person')}",
                    }

                elif action == "calibrate_user":
                    mode = cmd.get("mode", "save_manual")
                    cur_mar = latest_mouth_sample.get("mar")
                    cur_w = latest_mouth_sample.get("width_px")

                    if mode == "capture_closed":
                        if cur_mar is None:
                            res = {"status": "ERROR_NO_FACE", "output": "No live face detected — look at Person Cam first."}
                        else:
                            latest_mouth_sample["closed_mar"] = float(cur_mar)
                            res = {
                                "status": "CLOSED_MOUTH_CAPTURED",
                                "closed_mar": round(float(cur_mar), 3),
                                "output": f"Captured closed-mouth MAR = {cur_mar:.3f}. Now open comfortably and click '2. Open Mouth'.",
                            }
                    elif mode == "capture_open":
                        if cur_mar is None:
                            res = {"status": "ERROR_NO_FACE", "output": "No live face detected — look at Person Cam first."}
                        else:
                            closed = float(latest_mouth_sample.get("closed_mar") or 0.02)
                            open_m = float(cur_mar)
                            if open_m <= closed + 0.04:
                                res = {"status": "ERROR_TOO_CLOSE_MAR", "output": f"Open MAR ({open_m:.2f}) is too close to closed ({closed:.2f}). Open wider and try again."}
                            else:
                                new_thr = round(max(0.10, min(0.60, closed + 0.55 * (open_m - closed))), 3)
                                cal = feeding_detector.set_calibration(mar_open_threshold=new_thr)
                                cfg = load_config()
                                cfg["feeding_vision"] = cal
                                save_config(cfg)
                                res = {
                                    "status": "USER_MAR_CALIBRATED",
                                    "calibration": cal,
                                    "output": f"Calibrated MAR threshold = {new_thr:.3f} (closed={closed:.2f}, open={open_m:.2f}) and saved to config/elrobot.json.",
                                }
                    elif mode == "capture_distance":
                        if not cur_w:
                            res = {"status": "ERROR_NO_FACE", "output": "No live face detected — sit in eating position first."}
                        else:
                            new_w = max(40, min(260, int(round(float(cur_w) * 1.25))))
                            cal = feeding_detector.set_calibration(standoff_mouth_width_px=new_w)
                            cfg = load_config()
                            cfg["feeding_vision"] = cal
                            save_config(cfg)
                            res = {
                                "status": "USER_DISTANCE_CALIBRATED",
                                "calibration": cal,
                                "output": f"Calibrated standoff width = {new_w}px (from eating width {cur_w}px) and saved to config/elrobot.json.",
                            }
                    elif mode == "reset_defaults":
                        cal = feeding_detector.set_calibration(mar_open_threshold=0.26, standoff_mouth_width_px=95)
                        cfg = load_config()
                        cfg["feeding_vision"] = cal
                        save_config(cfg)
                        res = {"status": "CALIBRATION_RESET", "calibration": cal, "output": "Reset user calibration to defaults (MAR=0.26, Standoff=95px)."}
                    else:
                        mar_val = cmd.get("mar_open_threshold")
                        w_val = cmd.get("standoff_mouth_width_px")
                        cal = feeding_detector.set_calibration(
                            mar_open_threshold=float(mar_val) if mar_val is not None else None,
                            standoff_mouth_width_px=int(w_val) if w_val is not None else None,
                        )
                        cfg = load_config()
                        cfg["feeding_vision"] = cal
                        save_config(cfg)
                        res = {
                            "status": "USER_CALIBRATION_SAVED",
                            "calibration": cal,
                            "output": f"Saved user calibration to config/elrobot.json: MAR={cal['mar_open_threshold']}, Standoff={cal['standoff_mouth_width_px']}px.",
                        }

                # --- 1. CLI Execution Integration ---
                elif action == "run_cli":
                    cli_cmd = cmd.get("command", "").strip()
                    allowed_prefixes = [
                        "check", "test", "preflight", "hw", "demo",
                        "view-camera", "apriltags", "sdk-check", "sync", "feed",
                    ]
                    parts = cli_cmd.split()
                    if not parts or parts[0] not in allowed_prefixes:
                        res = {"status": "ERROR", "output": f"Command '{cli_cmd}' is not allowed or unrecognized."}
                    else:
                        full_cmd = ["./cli.sh"] + parts
                        run_res = subprocess.run(
                            full_cmd,
                            capture_output=True,
                            text=True,
                            timeout=60,
                        )
                        output = run_res.stdout + ("\n" + run_res.stderr if run_res.stderr else "")
                        res = {
                            "status": "SUCCESS" if run_res.returncode == 0 else f"EXIT_{run_res.returncode}",
                            "output": output[-2000:] if output else "(No output)",
                            "returncode": run_res.returncode,
                        }

                elif action == "teleop_start":
                    with teleop_lock:
                        if teleop_process is None or teleop_process.poll() is not None:
                            st_cfg = load_config().get("station", {})
                            leader_bus = st_cfg.get("leader_bus", "5B61037051")
                            follower_bus = st_cfg.get("bus", "5B61034962")
                            teleop_process = subprocess.Popen(
                                [
                                    sys.executable,
                                    "scripts/teleop_sync.py",
                                    "--leader", leader_bus,
                                    "--follower", follower_bus,
                                ],
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL,
                            )
                            res = {"status": "TELEOP_STARTED", "leader": leader_bus, "follower": follower_bus}
                        else:
                            res = {"status": "TELEOP_ALREADY_RUNNING"}

                elif action == "teleop_stop":
                    with teleop_lock:
                        if teleop_process is not None and teleop_process.poll() is None:
                            teleop_process.terminate()
                            teleop_process.wait(timeout=2.0)
                            teleop_process = None
                            res = {"status": "TELEOP_STOPPED"}
                        else:
                            res = {"status": "TELEOP_NOT_RUNNING"}

                elif action == "relax_leader":
                    st_cfg = load_config().get("station", {})
                    leader_bus = st_cfg.get("leader_bus", "5B61037051")
                    env = {**os.environ, "ELROBOT_BUS": leader_bus}
                    run_res = subprocess.run(
                        [sys.executable, "scripts/hw_day.py", "torque", "off"],
                        capture_output=True,
                        text=True,
                        timeout=15,
                        env=env,
                    )
                    output = run_res.stdout + ("\n" + run_res.stderr if run_res.stderr else "")
                    res = {
                        "status": "LEADER_TORQUE_OFF" if run_res.returncode == 0 else f"ERROR_EXIT_{run_res.returncode}",
                        "leader": leader_bus,
                        "output": output[-1000:] if output else f"Torque disabled on leader {leader_bus}",
                    }

                elif action == "swap_arms":
                    cfg = load_config()
                    st_cfg = dict(cfg.get("station") or {})
                    old_follower = st_cfg.get("bus", "5B61034962")
                    old_leader = st_cfg.get("leader_bus", "5B61037051")
                    st_cfg["bus"] = old_leader
                    st_cfg["leader_bus"] = old_follower
                    cfg["station"] = st_cfg
                    save_config(cfg)
                    res = {
                        "status": "ARMS_SWAPPED",
                        "master_bus": st_cfg["leader_bus"],
                        "slave_bus": st_cfg["bus"],
                        "output": f"Swapped roles in config/elrobot.json: Master={st_cfg['leader_bus']}, Slave={st_cfg['bus']}",
                    }

                elif action == "estop":
                    with teleop_lock:
                        if teleop_process is not None and teleop_process.poll() is None:
                            teleop_process.terminate()
                            teleop_process = None
                    subprocess.run(["python3", "scripts/hw_day.py", "stop"], capture_output=True)
                    res = {"status": "EMERGENCY_STOP_EXECUTED"}

                elif action == "teach":
                    name = cmd.get("name", "point_1").strip()
                    run_res = subprocess.run(["python3", "scripts/hw_day.py", "teach", name], capture_output=True, text=True)
                    res = {"status": "WAYPOINT_TEACH_OK", "output": run_res.stdout}

                elif action == "home":
                    res = mcp_server.reset_home()

                elif action == "pick":
                    res = mcp_server.pick_at(cmd.get("x", -60.0), cmd.get("y", 180.0))

                elif action == "place":
                    res = mcp_server.place_at(cmd.get("x", -130.0), cmd.get("y", 210.0))

                elif action == "perturb":
                    res = mcp_server.simulate_perturbation(
                        cmd.get("object_id", "blue_cube_01"),
                        cmd.get("x", -30.0),
                        cmd.get("y", 195.0),
                    )

                elif action == "run_tests":
                    test_run = subprocess.run(["python3", "-m", "pytest", "tests/"], capture_output=True, text=True)
                    passed = "passed" in test_run.stdout
                    res = {
                        "status": "TESTS_PASSED" if passed else "TESTS_FAILED",
                        "output": test_run.stdout[-1500:],
                    }

                elif action in ("feed_grapes", "feed_spoon"):
                    mode = "grapes" if action == "feed_grapes" else "spoon"
                    feed_res = run_camera_feeding_cycle(
                        mode=mode,
                        mcp_server=mcp_server,
                        preferred_camera=int(cmd.get("camera", 4)),
                    )
                    latest_feeding_overlay_b64 = feed_res.get("annotated_image_base64")
                    res = {
                        "status": f"FEEDING_{mode.upper()}_COMPLETE",
                        "camera_source": feed_res["camera_source"],
                        "detections": feed_res["detections"],
                        "output": "\n".join(feed_res["steps"]),
                    }

                elif action == "run_demo":
                    mcp_server.reset_home()
                    mcp_server.simulate_perturbation("blue_cube_01", -30.0, 195.0)
                    pick1 = mcp_server.pick_at(-60.0, 180.0)
                    v1 = mcp_server.verify_grasp()
                    pick2 = mcp_server.pick_at(-30.0, 195.0)
                    v2 = mcp_server.verify_grasp()
                    place_res = mcp_server.place_at(-130.0, 210.0)
                    mcp_server.reset_home()
                    res = {
                        "status": "AUTONOMOUS_DEMO_COMPLETED",
                        "first_pick": pick1.get("status"),
                        "first_verify": v1.get("status"),
                        "recovered_pick": pick2.get("status"),
                        "second_verify": v2.get("status"),
                        "place": place_res.get("status"),
                    }
                else:
                    res = {"status": f"UNKNOWN_ACTION_{action}"}

            except Exception as e:
                res = {"status": f"ERROR: {str(e)}"}

            self._send_json(res)
            return

        self.send_response(404)
        self.end_headers()


def start_server(port=SERVER_PORT):
    camera_hub.discover(force=True)
    with ThreadingHTTPServer(("", port), MissionControlHandler) as httpd:
        print("============================================================")
        print("  NormaCore Mission Control Running at:")
        print(f"  --> http://localhost:{port}")
        print("============================================================")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server.")
            httpd.server_close()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else SERVER_PORT
    start_server(port)
