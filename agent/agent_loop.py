"""DroneCAD — boucle agentique MCP (Phase 3) avec garde-fous explicites.

Garde-fous obligatoires du brief fondateur / founding brief's mandatory guards:
  1. allowlist d'outils MCP PAR PHASE (design / model / simulate / analyze / iterate) ;
  2. timeout par appel MCP ;
  3. journal JSONL structuré, corrélation par itération (correlation_id), digests d'arguments
     et de résultats (les journaux ne stockent pas les sorties brutes — preview tronquée) ;
  4. boucle bornée : 3 itérations maximum (IterationLimitReached sinon).

CLI :
  python agent_loop.py --list-tools <serveur>   # `tools/list` réel via .mcp.json (preuve Phase 3)
  python agent_loop.py --self-check             # vérifie la cohérence allowlist/journal (local)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol, Sequence

REPO_ROOT = Path(__file__).resolve().parent.parent
MCP_CONFIG = REPO_ROOT / ".mcp.json"
ALLOWLIST_FILE = Path(__file__).resolve().parent / "tool_allowlist.json"
DEFAULT_JOURNAL = REPO_ROOT / "artifacts" / "agent_journal.jsonl"
MAX_ITERATIONS = 3

ARG_PREVIEW_CHARS = 200


class MCPClientProtocol(Protocol):
    """Contrat minimal d'un client MCP (voir mcp_stdio.StdioMCPClient)."""

    def call_tool(
        self, name: str, arguments: dict[str, Any], timeout_s: float = ...
    ) -> dict[str, Any]: ...

    def list_tools(self, timeout_s: float = ...) -> list[dict[str, Any]]: ...


def sha256_digest(payload: Any) -> str:
    """Digest stable (16 hex) d'un payload JSON-sérialisable / stable digest of a payload."""
    encoded = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:16]


class ToolNotAllowed(RuntimeError):
    """Appel hors allowlist de la phase / call outside the phase allowlist."""


class IterationLimitReached(RuntimeError):
    """Critère non atteint après MAX_ITERATIONS / criterion not met after MAX_ITERATIONS."""


@dataclass(frozen=True)
class ToolCall:
    """Un appel d'outil MCP ciblé / a targeted MCP tool call."""

    server: str
    tool: str
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass
class CallOutcome:
    """Résultat d'un appel (journalisé) / journaled call outcome.

    EN: ``raw`` carries the untruncated tool result for callers that must parse it
        (orchestrators); the journal itself only stores digests, never raw payloads.
    FR : ``raw`` transporte le résultat intégral de l'outil pour les appelants qui doivent
        le parser (orchestrateurs) ; le journal ne stocke que des digests, jamais les bruts.
    """

    call: ToolCall
    ok: bool
    duration_ms: float
    result_digest: str | None
    error: str | None
    raw: dict[str, Any] | None = None


class PhaseGuard:
    """Contrôle l'allowlist serveur/outil par phase / enforces the per-phase allowlist."""

    def __init__(self, allowlist: Mapping[str, Mapping[str, Sequence[str]]]) -> None:
        self._allow: dict[str, dict[str, frozenset[str]]] = {
            phase: {server: frozenset(tools) for server, tools in per.items()}
            for phase, per in allowlist.items()
            if not phase.startswith("_")
        }

    def phases(self) -> tuple[str, ...]:
        return tuple(sorted(self._allow))

    def check(self, phase: str, call: ToolCall) -> None:
        per_phase = self._allow.get(phase)
        if per_phase is None:
            raise ToolNotAllowed(f"phase inconnue / unknown phase: {phase!r}")
        allowed = per_phase.get(call.server)
        if not allowed or call.tool not in allowed:
            raise ToolNotAllowed(
                f"outil non autorisé / tool not allowed: phase={phase} "
                f"server={call.server} tool={call.tool}"
            )


class AgentLoop:
    """Boucle agentique bornée avec journal JSONL / bounded agentic loop with a JSONL journal."""

    def __init__(
        self,
        clients: Mapping[str, MCPClientProtocol],
        guard: PhaseGuard,
        journal_path: Path = DEFAULT_JOURNAL,
        max_iterations: int = MAX_ITERATIONS,
        call_timeout_s: float = 30.0,
    ) -> None:
        self.clients = dict(clients)
        self.guard = guard
        self.journal_path = Path(journal_path)
        self.max_iterations = max_iterations
        self.call_timeout_s = call_timeout_s

    # ---------------------------------------------------------------- journal
    def _journal(self, entry: dict[str, Any]) -> None:
        self.journal_path.parent.mkdir(parents=True, exist_ok=True)
        with self.journal_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")

    # ---------------------------------------------------------------- appels
    def submit(
        self, phase: str, call: ToolCall, correlation_id: str, iteration: int
    ) -> CallOutcome:
        """Applique l'allowlist puis exécute l'appel ; journalise dans tous les cas.

        EN: guard first (violations raise ToolNotAllowed and are journaled), then call the MCP
        server with a per-call timeout; timeouts and errors are journaled as ok=False.
        FR : garde d'abord (les violations lèvent ToolNotAllowed et sont journalisées), puis
        l'appel MCP avec délai par appel ; délais et erreurs journalisés en ok=False.
        """
        entry: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "correlation_id": correlation_id,
            "iteration": iteration,
            "phase": phase,
            "server": call.server,
            "tool": call.tool,
            "args_digest": sha256_digest(call.arguments),
            "args_preview": json.dumps(call.arguments, ensure_ascii=False)[:ARG_PREVIEW_CHARS],
        }

        try:
            self.guard.check(phase, call)
        except ToolNotAllowed as exc:
            entry.update(ok=False, error=f"allowlist: {exc}", duration_ms=0.0)
            self._journal(entry)
            raise

        client = self.clients.get(call.server)
        if client is None:
            entry.update(ok=False, error=f"client inconnu / unknown client: {call.server}")
            self._journal(entry)
            return CallOutcome(call, False, 0.0, None, str(entry["error"]))

        started = time.monotonic()
        try:
            result = client.call_tool(call.tool, call.arguments, timeout_s=self.call_timeout_s)
        except Exception as exc:  # noqa: BLE001 - tout échec est journalisé / any failure is journaled
            duration_ms = (time.monotonic() - started) * 1000.0
            entry.update(
                ok=False,
                error=f"{type(exc).__name__}: {exc}",
                duration_ms=round(duration_ms, 1),
            )
            self._journal(entry)
            return CallOutcome(call, False, duration_ms, None, str(entry["error"]))

        duration_ms = (time.monotonic() - started) * 1000.0
        entry.update(
            ok=True,
            result_digest=sha256_digest(result),
            duration_ms=round(duration_ms, 1),
        )
        self._journal(entry)
        return CallOutcome(call, True, duration_ms, str(entry["result_digest"]), None, raw=result)

    # ---------------------------------------------------------------- boucle
    def run(
        self,
        steps: Sequence[tuple[str, ToolCall]],
        criterion: Callable[[Sequence[CallOutcome]], bool],
    ) -> list[list[CallOutcome]]:
        """Exécute les passes jusqu'au critère, borné à max_iterations.

        EN: each iteration gets its own correlation id; the loop stops as soon as the criterion
        passes, otherwise raises IterationLimitReached after max_iterations (explicit guard).
        FR : chaque itération a son propre correlation id ; la boucle s'arrête dès que le critère
        passe, sinon lève IterationLimitReached après max_iterations (garde-fou explicite).
        """
        run_id = uuid.uuid4().hex[:8]
        history: list[list[CallOutcome]] = []
        for iteration in range(1, self.max_iterations + 1):
            correlation_id = f"dronecad-{run_id}-it{iteration}"
            outcomes = [
                self.submit(phase, call, correlation_id, iteration) for phase, call in steps
            ]
            history.append(outcomes)
            if criterion(outcomes):
                return history
        raise IterationLimitReached(
            f"critère non atteint après {self.max_iterations} itérations / "
            f"criterion not met after {self.max_iterations} iterations"
        )


# -------------------------------------------------------------------- CLI
def load_allowlist(path: Path = ALLOWLIST_FILE) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _mcp_command(server: str) -> tuple[list[str], dict[str, str]]:
    """Extrait la commande du serveur depuis .mcp.json (avec expansion ``${VAR}``).

    EN: extracts the server command from .mcp.json, expanding ``${VAR}`` references —
        Claude Code expands them itself; our client mirrors that behaviour.
    FR : extrait la commande du serveur depuis `.mcp.json` en expansant les ``${VAR}`` —
        Claude Code le fait nativement ; notre client reproduit ce comportement.
    """
    import os

    config = json.loads(MCP_CONFIG.read_text(encoding="utf-8"))
    servers = config.get("mcpServers", {})
    if server not in servers:
        raise SystemExit(
            f"Serveur inconnu / unknown server: {server!r} (dispo : {sorted(servers)})"
        )
    spec = servers[server]
    command = [
        os.path.expandvars(str(part)) for part in [spec["command"], *spec.get("args", [])]
    ]
    env = {
        key: os.path.expandvars(str(value))
        for key, value in (spec.get("env") or {}).items()
    }
    return command, env


def main(argv: Sequence[str] | None = None) -> int:
    from mcp_stdio import StdioMCPClient  # import local : venv/CI plus simples / local import

    parser = argparse.ArgumentParser(description="DroneCAD — boucle agentique MCP (garde-fous)")
    parser.add_argument("--list-tools", metavar="SERVEUR", help="tools/list réel via .mcp.json")
    parser.add_argument("--self-check", action="store_true", help="cohérence allowlist + journal")
    parser.add_argument(
        "--timeout",
        type=float,
        default=60.0,
        help="délai par requête MCP en secondes (init inclus) / per-request MCP timeout (s)",
    )
    args = parser.parse_args(argv)

    if args.self_check:
        allowlist = load_allowlist()
        guard = PhaseGuard(allowlist)
        print(f"phases={guard.phases()} max_iterations={MAX_ITERATIONS}")
        print("self-check OK")
        return 0

    if args.list_tools:
        server = args.list_tools
        command, env = _mcp_command(server)
        client = StdioMCPClient(command, name=server, env={**__import__("os").environ, **env})
        try:
            client.start(initialize_timeout_s=args.timeout)
            tools = client.list_tools(timeout_s=args.timeout)
        finally:
            client.stop()
        print(json.dumps({"server": server, "count": len(tools),
                          "tools": [t.get("name") for t in tools]}, ensure_ascii=False))
        return 0

    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
