"""DroneCAD — client MCP stdio minimal (JSON-RPC 2.0 sur stdin/stdout).

EN: the subset of the MCP protocol needed to probe a server (`tools/list`) and call tools
    (`tools/call`), with a per-request timeout enforced by a queue + reader thread.
    Standard library only — no external dependency.
FR : le sous-ensemble du protocole MCP nécessaire pour sonder un serveur (`tools/list`) et
    appeler des outils (`tools/call`), avec un délai par requête appliqué par une file + un
    thread lecteur. Bibliothèque standard uniquement — aucune dépendance externe.
"""

from __future__ import annotations

import json
import queue
import subprocess
import threading
import time
from typing import Any, Sequence

PROTOCOL_VERSION = "2025-06-18"


class MCPError(RuntimeError):
    """Erreur JSON-RPC retournée par le serveur / JSON-RPC error returned by the server."""


class MCPTimeout(MCPError):
    """Délai dépassé pour une requête / request timed out."""


class StdioMCPClient:
    """Lance un serveur MCP stdio et parle JSON-RPC 2.0.

    EN: spawns the server as a subprocess (stdio transport) and speaks JSON-RPC 2.0.
    FR : lance le serveur en sous-processus (transport stdio) et parle JSON-RPC 2.0.
    """

    def __init__(
        self,
        command: Sequence[str],
        name: str = "mcp",
        env: dict[str, str] | None = None,
        cwd: str | None = None,
    ) -> None:
        self.command = list(command)
        self.name = name
        self._env = env
        self._cwd = cwd
        self._proc: subprocess.Popen[str] | None = None
        self._inbox: queue.Queue[dict[str, Any]] = queue.Queue()
        self._next_id = 0

    # ---------------------------------------------------------------- cycle de vie
    def start(self) -> None:
        if self._proc is not None:
            return
        self._proc = subprocess.Popen(
            self.command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            bufsize=1,
            env=self._env,
            cwd=self._cwd,
        )
        threading.Thread(target=self._read_loop, daemon=True).start()
        self._request(
            "initialize",
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "dronecad", "version": "0.1.0"},
            },
            timeout_s=30.0,
        )
        self._notify("notifications/initialized", {})

    def stop(self) -> None:
        proc = self._proc
        self._proc = None
        if proc is not None:
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except Exception:  # noqa: BLE001 - arrêt best-effort / best-effort shutdown
                proc.kill()

    def __enter__(self) -> "StdioMCPClient":
        self.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self.stop()

    # ---------------------------------------------------------------- protocole
    def _read_loop(self) -> None:
        assert self._proc is not None and self._proc.stdout is not None
        for line in self._proc.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                self._inbox.put(json.loads(line))
            except json.JSONDecodeError:
                continue  # EN: non-JSON noise / FR : bruit non JSON ignoré

    def _wait_for(self, request_id: int, timeout_s: float) -> dict[str, Any]:
        deadline = time.monotonic() + timeout_s
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise MCPTimeout(
                    f"{self.name}: délai dépassé / timeout after {timeout_s}s (id={request_id})"
                )
            try:
                payload = self._inbox.get(timeout=min(remaining, 0.25))
            except queue.Empty:
                continue
            if payload.get("id") == request_id:
                if "error" in payload:
                    raise MCPError(
                        f"{self.name}: erreur JSON-RPC / JSON-RPC error: {payload['error']}"
                    )
                return payload.get("result", {})

    def _request(self, method: str, params: dict[str, Any], timeout_s: float) -> dict[str, Any]:
        assert self._proc is not None and self._proc.stdin is not None, (
            "client non démarré / client not started"
        )
        self._next_id += 1
        request_id = self._next_id
        message = {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}
        self._proc.stdin.write(json.dumps(message) + "\n")
        self._proc.stdin.flush()
        return self._wait_for(request_id, timeout_s)

    def _notify(self, method: str, params: dict[str, Any]) -> None:
        assert self._proc is not None and self._proc.stdin is not None
        message = {"jsonrpc": "2.0", "method": method, "params": params}
        self._proc.stdin.write(json.dumps(message) + "\n")
        self._proc.stdin.flush()

    # ---------------------------------------------------------------- API utilisateur
    def list_tools(self, timeout_s: float = 20.0) -> list[dict[str, Any]]:
        """Retourne la liste des outils du serveur / returns the server tool list."""
        result = self._request("tools/list", {}, timeout_s)
        return list(result.get("tools", []))

    def call_tool(
        self, name: str, arguments: dict[str, Any], timeout_s: float = 30.0
    ) -> dict[str, Any]:
        """Appelle un outil / calls a tool."""
        return self._request("tools/call", {"name": name, "arguments": arguments}, timeout_s)
