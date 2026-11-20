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
