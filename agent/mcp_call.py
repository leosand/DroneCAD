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
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from agent_loop import _mcp_command, mcp_environment, mcp_working_directory
from mcp_stdio import StdioMCPClient

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
    client = StdioMCPClient(
        command,
        name=args.server,
        env=mcp_environment(args.server, env),
        cwd=mcp_working_directory(args.server),
    )
    try:
        client.start(initialize_timeout_s=args.timeout)
        result = client.call_tool(args.tool, call_args, timeout_s=args.timeout)
    finally:
        client.stop()

    # EN: Windows consoles default to cp1252 and crash on non-ASCII tool results (shodh-memory
    #     returns an emoji in its stats) — force UTF-8 on the way out.
    # FR : les consoles Windows sont en cp1252 et plantent sur les résultats non ASCII
    #     (shodh-memory renvoie un emoji dans ses statistiques) — forcer l'UTF-8 en sortie.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    print(json.dumps(result, ensure_ascii=False)[:MAX_PRINT_CHARS])
    return 0


if __name__ == "__main__":
    sys.exit(main())
