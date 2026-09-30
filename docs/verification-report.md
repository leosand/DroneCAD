# Verification report

Acceptance status of the project as of v0.3.0, with the evidence behind each item and the deviations from the original brief.

## Acceptance checklist

| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | Local model resident on GPU, tokens per second reported | Passed | `gpt-oss:20b`, 100% GPU at context 8192, 115.44 tokens per second, 1,463 MiB free |
| 2 | Compose file valid, containers start as non-root | Passed | `docker compose config` OK, two services up, user ID 1000, port 3030 on loopback only |
| 3 | Every MCP server answers a real `tools/list` | Passed | 5 of 5 (31, 83, 20, 15, 38 tools) plus live calls |
| 4 | Humanoid stands 10 seconds in Gazebo | Passed | z = 1.065 m; 1.056 m after a squat |
| 5 | Full agent loop end to end | Passed | `E2E_OK`, STEP and STL, BLEND and GLB, bag of 11,526 messages, effort diagnostic |
| 6 | CI green | Passed | All jobs green (validate, lint, container-tests, secret-scan) |
| 7 | No secret, no public port, clean image scan | Passed | `validate_stack.py`, gitleaks, Trivy with no fixable HIGH or CRITICAL finding |
| 8 | Audited reference repositories | Passed | Table below |

## Reference repositories audited (2026-09-18)

| Repository | Verdict | License | Notes |
|---|---|---|---|
| `wise-vision/ros2_mcp` | Adopt | MPL-2.0 | ROS 2 MCP over stdio, CI tests, rich toolset |
| `kakimochi/ros2-mcp-server` | Inspiration only | None detected | Stale, `/cmd_vel` only, targets Humble |
| `spkane/freecad-addon-robust-mcp-server` and image `ghcr.io/spkane/freecad-robust-mcp` | Adopt | MIT | Runs as a stdio MCP server; the repository `spkane/freecad-robust-mcp` does not exist |
| `neka-nat/freecad-mcp` | Adopt (upstream) | MIT | `uvx freecad-mcp`, upstream of the previous entry |
| `binabik-ai/mcp-rosbags` | Fork if needed | Apache-2.0 | About a year stale, no CI; see ADR-0008 |
| `ahujasid/mcp-for-blender` | Adopt (provisional) | MIT | Blender 5.x compatibility was unverified at audit time |
| Blender Lab official MCP | Adopt or compare | GPL-3.0-or-later | Requires Blender 5.1 or later |
| `dfki-ric/phobos` | Avoid on Blender 4.2 and later | BSD-3-Clause | Tested on Blender 3.3 LTS, see ADR-0004 |
| `varun29ankuS/shodh-memory` | Adopt | Apache-2.0 | Local memory server, REST on port 3030 |
| `gazebosim/ros_gz` | Adopt | Apache-2.0 | Canonical ROS to Gazebo bridge |
| `gazebosim/gz-sim` (Harmonic) | Adopt | Apache-2.0 | Simulation core, long-term support |
| `ros-controls/ros2_control`, `moveit/moveit2` | Adopt | Apache-2.0, BSD-3-Clause | Control and planning stacks |

## Deviations from the original brief

1. The host is Windows, not Linux: ROS 2 and Gazebo run in WSL2 containers, Blender and FreeCAD on the host (ADR-0001).
2. `devstral:22b` does not exist and `qwen3-coder-next` is 52 GB, so the fallback rule selected `gpt-oss:20b` (ADR-0002).
3. An upstream crash requires a dedicated Ollama server, and the free-VRAM margin is 1,463 MiB against a strict 1.5 GiB (ADR-0007).
4. Phobos is unusable on Blender 4.2 and later, so URDF export uses a `bpy` script (ADR-0004).
5. MCP servers are spawned by the client, not run as compose services (ADR-0006).
6. Kimi Code does not read `.mcp.json`, so MCP entries are copied by hand.
7. GitHub secret scanning is unavailable on private repositories without Advanced Security, so gitleaks runs in CI as a compensating control.

## CI root causes found and fixed

- Windows checkout lost script executable bits, which failed the linter (`EXE001`).
- The robot spawn used a fixed 2-second timer and raced the Gazebo world load. A `spawn_ready.py` step now waits for the world service and retries.
- The rendering plugin (OGRE2) hung on runners without a display. A headless world without it is now used.
- A user ID without a `/etc/passwd` entry silenced gz-transport. Containers now run as user 1000.
- The Trivy step ran out of disk space exporting a 6.3 GB image. Unused toolchains are removed and the build cache is pruned first.
- A critical `anyio` vulnerability (CVE-2026-63374) was fixed with a bump in the vendored virtual environment, after earlier fixes for pillow, cryptography and python-multipart.

## Deferred work

- Real-time factor of 1 through GPU passthrough.
- MuJoCo for locomotion reinforcement learning (ADR-0003).
- Localization and speed of the Gazebo workspace if navigation is needed.
- A formal fork of `mcp-rosbags` according to ADR-0008.
- Retiring the dedicated Ollama server once the upstream crash is fixed (ADR-0007).
