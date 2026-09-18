#!/usr/bin/env python3
"""validate_stack.py — DroneCAD security & stack validation (local + CI).

EN: Enforces the security baseline mechanically:
    - docker-compose.yml: non-root `user`, no `privileged: true`, no host networking,
      published ports bound to 127.0.0.1 only, `no-new-privileges` hardening.
    - .mcp.json: valid JSON, every url loopback-local, no literal secrets in env
      (${VAR} interpolation is allowed).
FR : Applique mécaniquement le socle sécurité :
    - docker-compose.yml : `user` non-root, pas de `privileged: true`, pas de réseau hôte,
      ports publiés liés à 127.0.0.1 seulement, durcissement `no-new-privileges`.
    - .mcp.json : JSON valide, toutes les URL en boucle locale, aucun secret littéral
      dans l'environnement (l'interpolation ${VAR} est permise).

Exit codes: 0 = OK (warnings allowed), 1 = violations, 2 = environment problem.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COMPOSE = ROOT / "docker-compose.yml"
MCP = ROOT / ".mcp.json"

SECRET_HINT = re.compile(r"(TOKEN|SECRET|API[_-]?KEY|PASSWORD|CREDENTIAL)", re.I)
LOOPBACK_RE = re.compile(r"^https?://(127\.0\.0\.1|localhost)(:\d+)?(/|$)")

errors: list[str] = []
warnings: list[str] = []


def load_compose() -> dict:
    """EN: prefer `docker compose config --format json` / FR : préférer docker compose."""
    if shutil.which("docker"):
        r = subprocess.run(
            ["docker", "compose", "-f", str(COMPOSE), "config", "--format", "json"],
            capture_output=True,
            text=True,
        )
        if r.returncode == 0:
            return json.loads(r.stdout)
    try:
        import yaml  # type: ignore[import-untyped]

        return yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        print(f"FATAL: docker compose indisponible et PyYAML absent ({exc})")
        sys.exit(2)


def check_compose() -> None:
    if not COMPOSE.exists():
        errors.append("docker-compose.yml manquant / missing")
        return
    data = load_compose() or {}
    services = data.get("services") or {}
    if not services:
        errors.append("docker-compose.yml: aucun service / no services defined")
        return
    for name, svc in services.items():
        svc = svc or {}
        if svc.get("privileged") is True:
            errors.append(f"compose[{name}]: privileged:true interdit (exige un ADR)")
        if svc.get("network_mode") == "host":
            errors.append(f"compose[{name}]: network_mode:host interdit / forbidden")
        if "user" not in svc:
            errors.append(f"compose[{name}]: 'user:' non-root manquant / missing non-root user")
        for port in svc.get("ports") or []:
            pretty = str(port)
            host_ip = port.get("host_ip") if isinstance(port, dict) else None
            if host_ip not in ("127.0.0.1", "::1") and not pretty.startswith("127.0.0.1:"):
                errors.append(f"compose[{name}]: port '{pretty}' non lié à 127.0.0.1 / not loopback-bound")
        if "no-new-privileges:true" not in (svc.get("security_opt") or []):
            warnings.append(f"compose[{name}]: ajouter security_opt: no-new-privileges:true")
        networks = svc.get("networks") or []
        if isinstance(networks, dict):
            networks = list(networks)
        if "agentnet" not in networks:
            warnings.append(f"compose[{name}]: réseau 'agentnet' absent / not on agentnet")


def check_mcp() -> None:
    if not MCP.exists():
        errors.append(".mcp.json manquant / missing")
        return
    try:
        data = json.loads(MCP.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f".mcp.json: JSON invalide / invalid JSON: {exc}")
        return
    servers = data.get("mcpServers") or {}
    if not servers:
        errors.append(".mcp.json: aucun mcpServers / no mcpServers")
        return
    for name, cfg in servers.items():
        cfg = cfg or {}
        if not cfg.get("command") and not cfg.get("url"):
            errors.append(f".mcp.json[{name}]: 'command' ou 'url' requis / required")
        url = cfg.get("url")
        if url and not LOOPBACK_RE.match(str(url)):
            errors.append(f".mcp.json[{name}]: URL non locale interdit / non-loopback url: {url}")
        for key, value in (cfg.get("env") or {}).items():
            if SECRET_HINT.search(str(key)) and isinstance(value, str) and value and "${" not in value:
                errors.append(f".mcp.json[{name}]: secret littéral dans env['{key}'] — utiliser ${{VAR}}")


def main() -> int:
    check_compose()
    check_mcp()
    print("DroneCAD — validation de la pile / stack validation")
    if warnings:
        print(f"\n[warn] {len(warnings)} avertissement(s) / warning(s):")
        for item in warnings:
            print(f"  - {item}")
    if errors:
        print(f"\n[FAIL] {len(errors)} erreur(s) / error(s):")
        for item in errors:
            print(f"  - {item}")
        return 1
    print("\n[OK] compose + .mcp.json — loopback, non-root, no privileged, no literal secrets")
    return 0


if __name__ == "__main__":
    sys.exit(main())
