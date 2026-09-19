"""DroneCAD — appel direct d'un outil MCP (diagnostic & opérations, Phase 3).

EN: single tool call through the stdio MCP client, reusing the .mcp.json registry
    (spawn command + env). Prints the raw JSON-RPC result (truncated).
FR : appel d'un seul outil via le client MCP stdio, en réutilisant le registre `.mcp.json`
    (commande + env). Affiche le résultat JSON-RPC brut (tronqué).

Usage :
    python agent/mcp_call.py <serveur> <outil> ['{"arg": "valeur"}'] [--timeout N]
Exemples :
    python agent/mcp_call.py blender get_scene_info
    python agent/mcp_call.py freecad get_freecad_version
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from agent_loop import _mcp_command  # noqa: E402
from mcp_stdio import StdioMCPClient  # noqa: E402

MAX_PRINT_CHARS = 2000


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="DroneCAD — appel direct d'un outil MCP")
    parser.add_argument("server", help="serveur MCP (.mcp.json) : blender, freecad, ros2, rosbags, memory")
    parser.add_argument("tool", help="nom de l'outil / tool name")
    parser.add_argument("arguments", nargs="?", default="{}", help="arguments JSON (défaut : {})")
    parser.add_argument("--timeout", type=float, default=60.0, help="délai MCP (s)")
    args = parser.parse_args(argv)

    try:
        call_args = json.loads(args.arguments)
    except json.JSONDecodeError as exc:
        print(f"arguments JSON invalides / invalid JSON arguments: {exc}", file=sys.stderr)
        return 2

    command, env = _mcp_command(args.server)
    client = StdioMCPClient(command, name=args.server, env={**os.environ, **env})
    try:
        client.start(initialize_timeout_s=args.timeout)
        result = client.call_tool(args.tool, call_args, timeout_s=args.timeout)
    finally:
        client.stop()

    print(json.dumps(result, ensure_ascii=False)[:MAX_PRINT_CHARS])
    return 0


if __name__ == "__main__":
    sys.exit(main())
