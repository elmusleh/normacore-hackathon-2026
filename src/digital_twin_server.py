"""
Digital Twin Web Server for NormaCore Tabletop Manipulation.
Serves a 3D WebGL Digital Twin and live telemetry API on port 8080.
"""

import http.server
import socketserver
import json
import base64
import io
import os
import sys

# Ensure src is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mcp_server import NormaCoreMCPServer

SERVER_PORT = 8080
mcp_server = NormaCoreMCPServer()


class DigitalTwinRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
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
            station = mcp_server.station
            telemetry = station.get_arm_telemetry()
            view = mcp_server.get_calibrated_view()

            payload = {
                "arm_pose": telemetry["end_effector"],
                "gripper_state": telemetry["gripper_state"],
                "gripper_load": telemetry["gripper_load"],
                "held_object": telemetry["held_object"],
                "objects": station.objects,
                "target_zones": station.target_zones,
                "camera_base64": view["image_base64"],
            }
            body = json.dumps(payload).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        elif self.path == "/api/camera":
            view = mcp_server.get_calibrated_view()
            raw_bytes = base64.b64decode(view["image_base64"])
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(raw_bytes)))
            self.end_headers()
            self.wfile.write(raw_bytes)
            return

        super().do_GET()

    def do_POST(self):
        if self.path == "/api/command":
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length)
            try:
                cmd = json.loads(post_data.decode("utf-8"))
                action = cmd.get("action")

                if action == "pick":
                    res = mcp_server.pick_at(cmd.get("x", -60.0), cmd.get("y", 180.0))
                elif action == "place":
                    res = mcp_server.place_at(cmd.get("x", -130.0), cmd.get("y", 210.0))
                elif action == "home":
                    res = mcp_server.reset_home()
                elif action == "perturb":
                    res = mcp_server.simulate_perturbation(
                        cmd.get("object_id", "blue_cube_01"),
                        cmd.get("x", -30.0),
                        cmd.get("y", 195.0),
                    )
                elif action == "run_demo":
                    # Full autonomous loop: Pick -> Fail/Perturb -> Recover -> Place
                    mcp_server.reset_home()
                    mcp_server.simulate_perturbation("blue_cube_01", -30.0, 195.0)
                    pick_attempt1 = mcp_server.pick_at(-60.0, 180.0)
                    v1 = mcp_server.verify_grasp()
                    # Re-plan at new coordinate
                    pick_attempt2 = mcp_server.pick_at(-30.0, 195.0)
                    v2 = mcp_server.verify_grasp()
                    place_res = mcp_server.place_at(-130.0, 210.0)
                    mcp_server.reset_home()
                    res = {
                        "status": "AUTONOMOUS_DEMO_COMPLETED",
                        "first_pick": pick_attempt1.get("status"),
                        "first_verify": v1.get("status"),
                        "recovered_pick": pick_attempt2.get("status"),
                        "second_verify": v2.get("status"),
                        "place": place_res.get("status"),
                    }
                else:
                    res = {"status": "ERROR_UNKNOWN_ACTION"}
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
    with socketserver.TCPServer(("", port), DigitalTwinRequestHandler) as httpd:
        print(f"============================================================")
        print(f"  NormaCore Digital Twin Server Running at:")
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
