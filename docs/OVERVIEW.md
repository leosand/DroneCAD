# DroneCAD overview

**DroneCAD** is a local-first, agentic prototyping stack for humanoid robotics. A local LLM (`gpt-oss:20b`, served by Ollama) drives FreeCAD, Blender, ROS 2 Jazzy and Gazebo Harmonic through MCP (Model Context Protocol) servers. No prompt or model output has to leave your machine.

> Status: **v0.3.0**, a research prototype validated in simulation only. Nothing here has been tested on physical hardware, and LLM output must be reviewed by a human before any fabrication.

## What it does

The stack demonstrates an end-to-end loop, checked by an automated end-to-end test:

1. Design a part in FreeCAD (for example a bracket) and export STEP and STL files.
2. Import it into Blender and export BLEND and GLB files.
3. Simulate a 28-DoF humanoid model in Gazebo (headless) while recording a ROS 2 bag.
4. Inspect the recorded bag through the rosbags MCP server.

In the latest measured run, the loop recorded 11,526 messages and the humanoid stayed standing for 10 simulated seconds (base height about 1.06 m).

## MCP servers

| Server | Role | Notes |
|---|---|---|
| `freecad` | Parametric CAD | About 83 tools; bridge ports 9875 and 9877; started by the agent |
| `blender` | Meshes and scenes | Add-on v1.7, port 9876, about 31 tools; `get_scene_info` requires a `user_prompt` argument |
| `ros2` | ROS 2 topics, nodes, services | Runs inside the container image |
| `rosbags` | Read and diagnose bags | Vendored as a pinned git submodule (`vendor/`); needs the `DRONECAD_HOME` variable |
| `memory` | Local persistent memory | Self-hosted `shodh-memory` container; about 38 tools |

Servers are declared in `.mcp.json`. The agent loop applies a per-phase tool allowlist, a per-call timeout and a JSONL audit journal with correlation identifiers.

## Prerequisites

| Item | Requirement |
|---|---|
| Container runtime | Docker with Compose (the project is developed on Windows with WSL2 and Docker) |
| LLM runtime | [Ollama](https://ollama.com) with `gpt-oss:20b` (about 14 GB download) |
| GPU or memory for the LLM | 16 GB of VRAM or unified memory is the practical minimum; 24 GB gives headroom for longer context. CPU offload works but is slower. |
| Disk space | About 6.3 GB for the ROS 2 image, plus the model. A local Trivy scan needs roughly 20 GB of temporary space. |
| CAD tools | FreeCAD 1.1.x and Blender with the DroneCAD add-on, to use the `freecad` and `blender` servers |

## Quick start

```bash
git clone --recurse-submodules https://github.com/leosand/DroneCAD.git
cd DroneCAD
cp .env.example .env    # never commit .env
# Edit .env: see the comments inside for each variable.
docker compose up -d --build
```

Then follow [USAGE.md](USAGE.md) to start the stack, connect an MCP client (Claude Code, Cursor or Kimi Code), drive the simulation and query a bag. [TESTING.md](TESTING.md) describes a six-level validation procedure, from a 30-second check to the full 10-minute loop.

### Memory server key

`SHODH_API_KEYS` is not a paid subscription. It is a secret you generate yourself for your own local memory container, for example with `python -c "import secrets; print(secrets.token_hex(24))"`. The MCP client reads the same value as `SHODH_API_KEY`. Keep it in `.env` only.

## Repository layout

| Path | Role |
|---|---|
| `agent/` | Agent loop, stdio MCP client and helper CLI (`mcp_call.py`) |
| `ws/` | ROS 2 workspace: humanoid description, Gazebo and control packages |
| `docker/` | Docker images (multi-stage ROS 2 Jazzy image) |
| `docker-compose.yml` | Service orchestration |
| `scripts/` | Setup and validation scripts |
| `vendor/` | Pinned third-party servers (git submodules, see `.gitmodules`) |
| `docs/` | Usage, testing, verified tools, hardware notes |
| `.mcp.json` | MCP server declarations |
| `AGENTS.md` | Instructions for AI coding agents |
| `ARCHITECTURE.md` | Design and decisions |
| `CHANGELOG.md` | Release history |

## Continuous integration

The workflow in `.github/workflows/ci.yml` runs two jobs:

- `lint`: Ruff on the Python code.
- `container-tests`: builds the image, runs `colcon` and a URDF check, starts a Gazebo server smoke test, runs a headless standing test inside the image, then scans the image with Trivy for HIGH and CRITICAL vulnerabilities.

## Known limitations and gotchas

- Gazebo containers must run as user `1000:1000`. A user id without a `/etc/passwd` entry makes gz-transport silent, so the robot never appears.
- The headless CI world (`flat_ground_headless.sdf`) has no rendering plugin. The world with camera and IMU sensors (`flat_ground.sdf`) needs a working rendering path; the camera was measured at a real-time factor of about 0.60 headless.
- Exporting `SHODH_API_KEYS` in your shell can break the `freecad` server, because it reads a `.env` file from its working directory. The agent starts MCP servers outside the repository to avoid this.
- Windows consoles using cp1252 can crash on emoji in server output; `agent/mcp_call.py` forces UTF-8.
- Simulation results are not proof of real-world behavior.

## Contributing and security

See [CONTRIBUTING.md](../CONTRIBUTING.md) and [SECURITY.md](../SECURITY.md). Never commit secrets or a populated `.env`.

## Suggested README header

```markdown
# DroneCAD

Local-first agentic prototyping stack for humanoid robotics: FreeCAD + Blender + ROS 2 Jazzy + Gazebo Harmonic + MCP, driven by a local model (gpt-oss:20b).

[![CI](https://github.com/leosand/DroneCAD/actions/workflows/ci.yml/badge.svg)](https://github.com/leosand/DroneCAD/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

[Overview](docs/OVERVIEW.md) | [Usage](docs/USAGE.md) | [Testing](docs/TESTING.md) | [Architecture](ARCHITECTURE.md) | [Contributing](CONTRIBUTING.md) | [Changelog](CHANGELOG.md)
```
