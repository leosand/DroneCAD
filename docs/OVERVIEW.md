# Architecture overview

This page is the short version. Detailed decisions are in [../ARCHITECTURE.md](../ARCHITECTURE.md).

## Components

| Component | Where it runs | Role |
|---|---|---|
| Ollama + `gpt-oss:20b` | Host | Local reasoning model, served on port 11499 by `scripts/start-ollama-gptoss.ps1` |
| Agent loop (`agent/`) | Host | Calls MCP tools with an allowlist per phase, a timeout per call and a JSONL journal |
| FreeCAD | Host (GUI open) | CAD bridge on ports 9875 (XML-RPC) and 9877 (socket) |
| Blender | Host (GUI open) | Add-on v1.7 on port 9876 |
| `ros2-jazzy` container | Docker | ROS 2 Jazzy, Gazebo Harmonic, MoveIt 2, the humanoid workspace and the `ros2` MCP server |
| `shodh-memory` container | Docker | Local persistent memory, port 3030 on loopback, data in the `shodh-data` volume |
| `rosbags` server | Host | Reads recorded bags through a pinned submodule in `vendor/` |

## Data flow of the end-to-end loop

1. The agent asks FreeCAD for a bracket and exports STEP and STL.
2. Blender imports the mesh and writes a master BLEND and a GLB.
3. Gazebo runs the 28-DoF humanoid headless while a bag records `/clock`, `/joint_states` and `/imu`.
4. The `rosbags` server checks for falls and joint effort. On failure the agent iterates, up to three times.

## Phases

| Phase | Content |
|---|---|
| 0 | Hardware probe and model choice |
| 1 | Multi-stage ROS 2 Jazzy image with Gazebo and MoveIt 2 |
| 2 | Humanoid packages: description, Gazebo and control (28 DoF) |
| 3 | Five MCP servers verified and the agentic loop with guardrails |
| 4 | CI with lint, container tests and Trivy; headless camera check |

## Continuous integration

`.github/workflows/ci.yml` runs two jobs. `lint` runs Ruff on `agent/`, `scripts/` and `ws/src/`. `container-tests` builds the image, runs `colcon` and the URDF tests, a Gazebo server smoke test and a headless standing test inside the image, then a Trivy scan.

## Known limitations

- Gazebo containers must run as user `1000:1000`. A user ID without a `/etc/passwd` entry silences gz-transport and the robot never appears.
- The headless CI world has no rendering plugin. With the camera and IMU enabled, the real-time factor measured 0.60 on a 4-core CPU (0.50 without the camera).
- Exporting `SHODH_API_KEYS` in your shell can stop the `freecad` server, because it reads a `.env` file from its working directory. The agent starts MCP servers outside the repository to avoid this.
- Kimi Code does not read `.mcp.json`; copy the five entries into its MCP configuration.
- Results come from simulation only. They do not prove real-world behavior.

## Future work

- Real-time factor of 1 through GPU passthrough.
- MuJoCo for locomotion reinforcement learning.
- A formal fork of the `rosbags` MCP server if the compatibility wrapper stops being enough.
