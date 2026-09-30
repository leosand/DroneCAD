# AGENTS.md

Entry point for AI coding agents working in this repository.

## Context

DroneCAD is a local-first agentic prototyping stack for humanoid robotics: Blender, FreeCAD, ROS 2 Jazzy, Gazebo Harmonic and MCP, driven by a local model (`gpt-oss:20b`). The reference host is Windows with Docker Desktop (WSL2) and a 16 GB NVIDIA GPU.

- Design decisions: [ARCHITECTURE.md](ARCHITECTURE.md).
- Verification status and known deviations: [docs/verification-report.md](docs/verification-report.md).
- Usage: [docs/USAGE.md](docs/USAGE.md). Tests: [docs/TESTING.md](docs/TESTING.md).

## Working rules

1. Write code comments and documentation in English.
2. Python 3.12 with strict type hints for the agent layer.
3. Security first: non-root containers, ports bound to `127.0.0.1`, no hard-coded secrets, no `privileged: true` without an ADR.
4. No silent TODOs. Record deferred work in `docs/verification-report.md`.
5. Use SemVer and keep `CHANGELOG.md` up to date under `[Unreleased]`.
6. Do not assume another local model without updating ADR-0002.
7. Source of truth order: code, then tests, then the verification report.
8. Run Gazebo containers as `--user 1000:1000`.

## Key commands

```bash
docker compose config -q            # validate the compose file
python scripts/validate_stack.py    # ports, privileged, secrets, MCP registry
docker compose up -d                # start the stack
ruff check agent scripts ws/src     # lint
```

## Agent scope

The MCP servers (`blender`, `freecad`, `ros2`, `rosbags`, `memory`) are spawned by the client, see ADR-0006 and `.mcp.json`. The agent loop must keep a per-phase tool allowlist, a per-call timeout and a JSON journal with correlation IDs.
