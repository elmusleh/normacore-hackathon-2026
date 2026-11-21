#!/usr/bin/env bash
# ==============================================================================
# cli.sh - Master CLI Runner for NormaCore Physical AI & Tabletop Robotics
# ==============================================================================
set -e

# Colors
C_RESET="\033[0m"
C_BOLD="\033[1m"
C_BLUE="\033[34m"
C_GREEN="\033[32m"
C_YELLOW="\033[33m"
C_RED="\033[31m"
C_CYAN="\033[36m"

print_header() {
    echo -e "${C_BOLD}${C_BLUE}================================================================${C_RESET}"
    echo -e "${C_BOLD}${C_CYAN}  NormaCore Physical AI & Tabletop Robotics — Master CLI Runner  ${C_RESET}"
    echo -e "${C_BOLD}${C_BLUE}================================================================${C_RESET}"
}

print_usage() {
    print_header
    echo -e "${C_BOLD}Usage:${C_RESET} ./cli.sh <command> [options]"
    echo ""
    echo -e "${C_BOLD}Testing & Simulation Commands:${C_RESET}"
    echo -e "  ${C_GREEN}test [filter]${C_RESET}       Run pytest test suite (e.g. ./cli.sh test test_kinematics)"
    echo -e "  ${C_GREEN}demo${C_RESET}                Run autonomous judge-perturbation recovery demo in terminal"
    echo -e "  ${C_GREEN}digital-twin [port]${C_RESET} Launch 3D WebGL Digital Twin server (Default: http://localhost:8080)"
    echo -e "  ${C_GREEN}view-camera${C_RESET}         Capture and save fresh calibrated camera image to sample_calibrated_view.png"
    echo -e "  ${C_GREEN}apriltags${C_RESET}           Generate printable/screen-displayable 4-corner AprilTags sheet"
    echo ""
    echo -e "${C_BOLD}Hardware & Station Runtime Commands:${C_RESET}"
    echo -e "  ${C_YELLOW}station${C_RESET}             Launch official pre-compiled Station binary (--web --tcp)"
    echo -e "  ${C_YELLOW}setup-serial${C_RESET}        Configure Linux USB permissions (dialout, udev rules) for ElRobot servos"
    echo -e "  ${C_YELLOW}mcp${C_RESET}                 Run Model Context Protocol (MCP) server for Claude / Codex"
    echo -e "  ${C_YELLOW}urdf${C_RESET}                Open official NormaCore online 3D URDF interactive viewer"
    echo ""
    echo -e "${C_BOLD}Hardware Day (ElRobot):${C_RESET}"
    echo -e "  ${C_GREEN}hw${C_RESET}                  Checklist, joint map, waypoints (start here)"
    echo -e "  ${C_GREEN}hw next${C_RESET}             Show or run the next open step"
    echo -e "  ${C_GREEN}hw run <n>${C_RESET}          Run step n;  ${C_GREEN}hw done <n>${C_RESET} marks a manual step"
    echo -e "  ${C_GREEN}hw identify${C_RESET}         Guided: nudge each motor and record which joint moved"
    echo -e "  ${C_GREEN}hw motors${C_RESET}           Live read-only table of motors 1-8"
    echo -e "  ${C_YELLOW}hw torque on|off${C_RESET}     On holds the current pose; off makes the arm limp"
    echo -e "  ${C_RED}hw jog <m> <steps>${C_RESET}   Move one motor (max ±200; type MOVE to confirm)"
    echo -e "  ${C_RED}hw probe-current <m>${C_RESET} Small move to measure peak current, suggests a threshold"
    echo -e "  ${C_GREEN}hw teach <name>${C_RESET}     Save the current pose of all 8 motors as a waypoint"
    echo -e "  ${C_GREEN}hw goto <name>${C_RESET}      Move all motors to a waypoint (shows plan; type MOVE)"
    echo -e "  ${C_GREEN}hw waypoints${C_RESET}        List taught waypoints"
    echo -e "  ${C_RED}hw stop${C_RESET}              Torque OFF on all motors (emergency)"
    echo -e "  ${C_CYAN}hw workspace${C_RESET}         Show workspace limits and whether they were measured"
    echo -e "  ${C_CYAN}hw bundle${C_RESET}            Pack logs, config and state for debugging or sharing"
    echo -e "  ${C_CYAN}logs [-f]${C_RESET}            Show the newest run log (-f follows it live)"
    echo -e "  ${C_CYAN}preflight${C_RESET}            Read-only ElRobot readiness check (writes logs/)"
    echo ""
    echo -e "${C_BOLD}Team Sync:${C_RESET}"
    echo -e "  ${C_CYAN}sync${C_RESET}                Fetch, then fast-forward if clean and behind (never stashes or force-pulls)"
    echo ""
    echo -e "${C_BOLD}General Commands:${C_RESET}"
    echo -e "  ${C_CYAN}help${C_RESET}                Display this help menu"
    echo -e "${C_BOLD}${C_BLUE}================================================================${C_RESET}"
}

COMMAND="${1:-help}"
shift || true

case "$COMMAND" in
    test)
        echo -e "${C_GREEN}[+] Running pytest test suite...${C_RESET}"
        if [ -n "$1" ]; then
            python3 -m pytest tests/test_pipeline.py -k "$1" -v
        else
            python3 -m pytest tests/test_pipeline.py -v
        fi
        ;;

    demo)
        echo -e "${C_GREEN}[+] Running Autonomous Recovery Demo...${C_RESET}"
        python3 src/agent_prompts.py
        ;;

    digital-twin)
        PORT="${1:-8080}"
        echo -e "${C_GREEN}[+] Launching 3D Digital Twin Server on http://localhost:${PORT}...${C_RESET}"
        if command -v xdg-open > /dev/null 2>&1; then
            (sleep 1 && xdg-open "http://localhost:${PORT}") &
        fi
        python3 src/digital_twin_server.py "$PORT"
        ;;

    station)
        echo -e "${C_YELLOW}[+] Launching NormaCore Station binary (Web: 8889, TCP: 8888)...${C_RESET}"
        if [ ! -f "bin/station" ]; then
            echo -e "${C_RED}[ERROR] bin/station binary not found.${C_RESET}"
            exit 1
        fi
        ./bin/station --web --tcp
        ;;

    setup-serial)
        echo -e "${C_YELLOW}[+] Running Linux USB serial permissions and udev setup...${C_RESET}"
        ./scripts/setup_usb_serial.sh
        ;;

    apriltags)
        echo -e "${C_GREEN}[+] Generating 4-corner AprilTags calibration sheet...${C_RESET}"
        python3 scripts/generate_apriltags.py
        if command -v xdg-open > /dev/null 2>&1; then
            xdg-open docs/apriltags_printable.html &
        fi
        ;;

    view-camera)
        echo -e "${C_GREEN}[+] Capturing fresh calibrated camera frame...${C_RESET}"
        python3 -c "
from src.mcp_server import NormaCoreMCPServer
import base64
s = NormaCoreMCPServer()
v = s.get_calibrated_view()
with open('sample_calibrated_view.png', 'wb') as f:
    f.write(base64.b64decode(v['image_base64']))
print('[OK] Saved fresh snapshot with metric grid to sample_calibrated_view.png')
"
        if command -v xdg-open > /dev/null 2>&1; then
            xdg-open sample_calibrated_view.png &
        fi
        ;;

    mcp)
        echo -e "${C_CYAN}[+] Starting MCP server (stdin/stdout)...${C_RESET}"
        python3 src/mcp_server.py
        ;;

    urdf)
        echo -e "${C_CYAN}[+] Opening NormaCore 3D Web Playground...${C_RESET}"
        if command -v xdg-open > /dev/null 2>&1; then
            xdg-open "https://normacore.dev/elrobot-urdf/"
        else
            echo "Browse to: https://normacore.dev/elrobot-urdf/"
        fi
        ;;

    hw)
        python3 scripts/hw_day.py "$@"
        ;;

    sync)
        # Fetch and fast-forward before implementing. Never stashes or force-pulls.
        bash scripts/agent_sync.sh "$@"
        ;;

    preflight)
        python3 scripts/hardware_preflight.py "$@"
        ;;

    logs)
        # Newest run log of any tool (hw, preflight, ...). -f follows it live.
        LATEST=$(ls -t logs/*.log 2>/dev/null | grep -v -- '-latest.log$' | head -1 || true)
        if [ -z "$LATEST" ]; then
            echo -e "${C_YELLOW}No logs yet. Run ./cli.sh preflight or ./cli.sh hw first.${C_RESET}"
            exit 1
        fi
        echo -e "${C_CYAN}--- ${LATEST} ---${C_RESET}"
        if [ "$1" = "-f" ]; then
            tail -n 80 -f "$LATEST"
        else
            tail -n 80 "$LATEST"
        fi
        ;;

    help|--help|-h)
        print_usage
        ;;

    *)
        echo -e "${C_RED}[ERROR] Unknown command: '$COMMAND'${C_RESET}"
        echo ""
        print_usage
        exit 1
        ;;
esac
