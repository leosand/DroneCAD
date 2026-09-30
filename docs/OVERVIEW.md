# DroneCAD overview

> This file holds a suggested header for the root `README.md`. Items in `<angle brackets>` must be verified by the maintainer before merging.

**DroneCAD** is a local-first, agentic prototyping stack for humanoid robotics. A local LLM (gpt-oss:20b served through Ollama) drives Blender, FreeCAD, ROS 2 Jazzy and Gazebo Harmonic via MCP (Model Context Protocol) tools. It runs on Windows with WSL2 and Docker.

## Suggested README header

```markdown
# DroneCAD

Local-first agentic prototyping stack for humanoid robotics: Blender + FreeCAD + ROS 2 Jazzy + Gazebo Harmonic + MCP, driven by a local model (gpt-oss:20b).

[![CI](https://github.com/leosand/DroneCAD/actions/workflows/ci.yml/badge.svg)](https://github.com/leosand/DroneCAD/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

[Quick start](#quick-start) | [Architecture](ARCHITECTURE.md) | [Docs](docs/README.md) | [Contributing](CONTRIBUTING.md) | [Changelog](CHANGELOG.md)
```

## Quick start

```bash
git clone --recurse-submodules https://github.com/leosand/DroneCAD.git
cd DroneCAD
cp .env.example .env   # never commit .env
docker compose up -d --build
```

Prerequisites to document: `<GPU/VRAM needed for gpt-oss:20b>`, `<Ollama version>`, `<disk space>`, `<WSL2 distribution>`.

## Repository layout

| Path | Role |
|---|---|
| `agent/` | LLM agent and MCP integration |
| `ws/` | ROS 2 workspace |
| `docker/` | Docker images |
| `docker-compose.yml` | Service orchestration |
| `scripts/` | Setup and helper scripts |
| `vendor/` | Third-party dependencies (git submodules, see `.gitmodules`) |
| `docs/` | Guides and reference |
| `.mcp.json` | MCP server declarations |
| `AGENTS.md` | Instructions for AI coding agents |

## Status and limitations

`<Describe what works, what is experimental, and known limits.>`
