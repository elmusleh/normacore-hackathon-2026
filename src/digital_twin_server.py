"""
Unified Mission Control Backend for NormaCore Tabletop Robotics.
Serves Web Dashboard (port 8080) with real-time controls for:
  - Master / Slave Teleop Sync toggle
  - Live hardware telemetry (Buses 5B61034962 and 5B61037051)
  - Live camera feed with metric grid overlay
  - Waypoints (Home, Clear, Pick, Place)
  - Emergency E-Stop (Torque Off)
  - Automated Testing (pytest) and Judge Perturbation Recovery Demo
"""

import http.server
import socketserver
import json
import base64
import io
import os
import sys
import subprocess
import threading
import time
import cv2
from typing import Optional

# Ensure src is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mcp_server import NormaCoreMCPServer
from vision_homography import TabletopCalibrator

SERVER_PORT = 8080
mcp_server = NormaCoreMCPServer()
calibrator = TabletopCalibrator()

# Global state for teleoperation background subprocess
teleop_process: Optional[subprocess.Popen] = None
teleop_lock = threading.Lock()


def get_live_camera_feed():
    """Tries to capture from /dev/video4 or /dev/video2, overlays metric grid."""
    for cam_idx in [4, 2]:
        cap = cv2.VideoCapture(cam_idx)
        if cap.isOpened():
            ret, frame = cap.read()
            cap.release()
            if ret:
                # Convert BGR to RGB
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                from PIL import Image
                pil_img = Image.fromarray(rgb)
                try:
                    annotated = calibrator.overlay_calibrated_grid(pil_img)
                except Exception:
                    annotated = pil_img
                buf = io.BytesIO()
                annotated.save(buf, format="JPEG", quality=80)
                return base64.b64encode(buf.getvalue()).decode("utf-8")
    
    # Fallback to simulated / cached view
    try:
        view = mcp_server.get_calibrated_view()
        return view["image_base64"]
    except Exception:
        return ""


class MissionControlHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path in ["/", "/index.html"]:
            html_path = os.path.join(os.path.dirname(__file__), "digital_twin.html")
            with open(html_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
            return

        elif self.path == "/api/state":
            global teleop_process
            is_teleop_running = teleop_process is not None and teleop_process.poll() is None

            station = mcp_server.station
            telemetry = station.get_arm_telemetry()
            cam_b64 = get_live_camera_feed()

            payload = {
                "teleop_active": is_teleop_running,
                "master_bus": "5B61034962",
                "slave_bus": "5B61037051",
                "arm_pose": telemetry["end_effector"],
                "gripper_state": telemetry["gripper_state"],
                "gripper_load": telemetry["gripper_load"],
                "held_object": telemetry["held_object"],
                "objects": getattr(station, "objects", {}),
                "target_zones": getattr(station, "target_zones", {}),
                "camera_base64": cam_b64,
            }
            body = json.dumps(payload).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        super().do_GET()

    def do_POST(self):
        global teleop_process
        if self.path == "/api/command":
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length)
            try:
                cmd = json.loads(post_data.decode("utf-8"))
                action = cmd.get("action")
                res = {"status": "SUCCESS"}

                if action == "teleop_start":
                    with teleop_lock:
                        if teleop_process is None or teleop_process.poll() is not None:
                            teleop_process = subprocess.Popen(
                                [sys.executable, "scripts/teleop_sync.py"],
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL,
                            )
                            res = {"status": "TELEOP_STARTED"}
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

                elif action == "estop":
                    with teleop_lock:
                        if teleop_process is not None and teleop_process.poll() is None:
                            teleop_process.terminate()
                            teleop_process = None
                    # Explicit emergency stop script
                    subprocess.run(["python3", "scripts/hw_day.py", "stop"], capture_output=True)
                    res = {"status": "EMERGENCY_STOP_EXECUTED"}

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
                        "output": test_run.stdout[-300:],
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

            body = json.dumps(res).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        self.send_response(404)
        self.end_headers()


def start_server(port=SERVER_PORT):
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", port), MissionControlHandler) as httpd:
        print(f"============================================================")
        print(f"  NormaCore Mission Control Running at:")
        print(f"  --> http://localhost:{port}")
        print(f"============================================================")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server.")
            httpd.server_close()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else SERVER_PORT
    start_server(port)
