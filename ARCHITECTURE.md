# ARCHITECTURE.md — DroneCAD

> EN: Architecture Decision Records (ADR) and current limits. / FR-CA : décisions d'architecture et limites actuelles.
> Each ADR follows: Context → Decision → Consequences → Alternatives considered.

---

## ADR-0001 — Execution platform: Windows host + Docker Desktop (WSL2)

**Date:** 2026-09-18 · **Status:** accepted

**Context.** The founding brief assumes a Linux host (`free -h`, containers with Gazebo, xvfb in CI). The actual target machine (measured 2026-09-18) is Windows with an RTX 4070 Ti SUPER, Docker 29.7.2 (Linux container mode, WSL2 backend), WSL2 Ubuntu available, Python 3.12.10, Ollama 0.34.0.

**Decision.** Host stays Windows: Blender 5.2 and CAD tools run natively (GUI + GPU); ROS 2 Jazzy, Gazebo Harmonic and MCP server containers run as Linux containers via Docker Desktop/WSL2. Equivalent probes are run with PowerShell (`Get-CimInstance Win32_OperatingSystem` etc.).

**Consequences.**
- Gazebo GUI inside containers is discouraged; validation is **headless** (`gz sim -s`, xvfb in CI). Interactive inspection uses `gz sim -g` on the host against a running server, to be validated in Phase 1/2.
- VRAM is shared between Windows apps and containers → keep the local model + Gazebo from running heavy GPU work simultaneously.
- CPU (Xeon W-2123, 4c/8t) is the RTF-1/1 risk factor, not the GPU — to be measured in Phase 2.

**Alternatives.** Native Linux reinstall (rejected: user platform constraint) · WSL2-native ROS install without Docker (rejected for now: spec requires compose isolation; may be revisited if WSLg/GPU passthrough proves necessary).

---

## ADR-0002 — Local agentic model: `gpt-oss:20b`

**Date:** 2026-09-18 · **Status:** accepted (bench in `docs/phase-0-hardware.md`)

**Context.** The brief's grid (valid 2026-09) proposes, in priority: `devstral:22b` → `gpt-oss:20b` → `qwen3-coder-next` → `gemma4:12b`, with the hard criterion "fully VRAM-resident with KV-cache margin on 16 GB" + benchmark ≥ 40 tok/s (downgrade below 25 tok/s) + ≥ 1.5 GB VRAM free while loaded.

**Registry reality (audited 2026-09-18, ollama.com/library).**
| Candidate | Actual state | Verdict |
|---|---|---|
| `devstral:22b` | **does not exist** — devstral tags are all 24B (14 GB, gen-1, ~1 year old) | rejected (spec's priority-1 tag unavailable) |
| `devstral-small-2:24b` | exists, 15 GB Q4_K_M (384K ctx, tools) | rejected: no KV-cache margin on a 16 376 MiB card (violates the ≥ 1.5 GB net criterion) |
| `qwen3-coder-next` | exists but **52 GB** (spec estimated ~16 GB) | rejected: does not fit |
| `gpt-oss:20b` | exists, 14 GB MXFP4, 128K ctx, tools; documented 16 GB-card agentic results | **adopted (priority 2 fallback, triggered by priority-1 unavailability)** |
| `gemma4:12b` | exists, 7.6 GB | kept as level-4 fallback |

**Decision.** `gpt-oss:20b`, pulled and benchmarked 2026-09-18; measured tok/s and residual VRAM recorded in `REPORT.md` / `docs/phase-0-hardware.md`. If the benchmark had come in < 25 tok/s or margin < 1.5 GB, downgrade to `gemma4:12b` or `num_ctx=8192` per the brief.

**Consequences.** Model = strong tool-calling agentic profile; small KV footprint (MXFP4 + GQA) suits 16 GB. Single-model setup for now; the design/modeling loop (Phase 3) will confirm real-world behavior on this stack.

**Alternatives.** Running a 30B MoE (`qwen3-coder:30b`, 19 GB) with partial CPU offload (rejected: violates full-residency criterion) · cloud models (rejected: local-first requirement).

---

## ADR-0003 — Simulation: Gazebo Harmonic now, MuJoCo recommended for future RL

**Date:** 2026-09-18 · **Status:** accepted

**Context.** The brief requires Gazebo Harmonic (`gz-sim8` series, LTS, EOL 2029 — audited) with the canonical `gazebosim/ros_gz` bridge (⚠️ `ros2/ros_gz` does not exist). The brief also asks to recommend MuJoCo as a future phase for RL locomotion.

**Decision.** Gazebo Harmonic is the simulation/validation environment for Phases 1–5 (native ROS 2 integration, joint-state/IMU/camera topics, ros2_control). **MuJoCo is recommended as a future phase** for reinforcement-learning of locomotion (contact-rich dynamics, much faster than real time, mature RL tooling); locomotion controllers trained in MuJoCo would be re-validated in Gazebo before hardware.

**Consequences.** Gazebo physics + 4-core CPU may not sustain RTF 1/1 with camera+IMU at high rate — measure in Phase 2, tune sensor rates, and document. MuJoCo would need a URDF/MJCF export path (Phase 2 must keep the URDF MJCF-compatible: single root, convex collision primitives).

---

## ADR-0004 — Geometry chain: Blender on host; Phobos is a risk on Blender ≥ 4.2

**Date:** 2026-09-18 · **Status:** accepted; URDF export method to be finalized in Phase 2

**Context.** The brief mandates Blender (host) + Phobos (DFKI, `dfki-ric/phobos`) for URDF/SDF/SMURF export, plus the official Blender Lab MCP server "if available". Audit findings: the **official Blender MCP exists** (GPL-3.0-or-later, v1.0.3 2026-09-11, requires Blender ≥ 5.1 — host has 5.2 ✅) but its client-side server CLI is not publicly confirmed yet; the community `mcp-for-blender` has a documented invocation (`uvx mcp-for-blender`) but unverified Blender 5.x support. **Phobos is tested on Blender 3.3 LTS and has open breakage issues on Blender 4.2** — no maintained Blender ≥ 4 fork was found.

**Decision.**
1. Blender stays on host (GUI + GPU). MCP registration ships with `mcp-for-blender` (verified invocation); Phase 3 evaluates switching to the official Blender Lab MCP once its setup is confirmed.
2. Phase 2 URDF export will **not** depend on Phobos working on Blender 5.2: primary path = deterministic `bpy` export script generating URDF/Xacro from a versioned master `.blend`; Phobos is kept as a conceptual reference (and optional path on an older Blender install). ADR to be updated with the delivered export script.

**Consequences.** The "`.blend` maître + script d'export reproductible" requirement is preserved; the Phobos dependency is de-risked rather than silently assumed.

---

## ADR-0005 — Security & isolation baseline

**Date:** 2026-09-18 · **Status:** accepted

**Decision.** Non-root users in all containers; **no** `privileged: true` (would require its own ADR); published ports bound to `127.0.0.1` only; named internal network `agentnet`; secrets only via env/secret stores, never committed (GitHub secret scanning + push protection enabled); CI actions pinned by SHA; `scripts/validate_stack.py` enforces these rules locally and in CI. Phase 3 adds tool allowlists per loop phase, per-call timeouts, and a structured JSON journal with correlation IDs.

**Rationale.** Localhost-only with no TLS is acceptable per brief; principle of least privilege is enforced mechanically, not by convention.

---

## ADR-0006 — MCP transport: stdio servers are client-spawned, not compose daemons

**Date:** 2026-09-18 · **Status:** accepted

**Context.** The brief lists `ros2-mcp`, `freecad-mcp`, `mcp-rosbags` as compose services. Audit shows all three are **stdio** MCP servers (spawned by the MCP client over stdin/stdout), not long-running daemons. Presenting them as compose services would require an unverified stdio↔socket bridge.

**Decision.** `docker-compose.yml` contains *runtime* services only (`ros2-jazzy`, `shodh-memory` REST). The stdio MCP servers are registered in `.mcp.json` and spawned by the agent client:
- `blender` → `uvx mcp-for-blender` (host),
- `freecad` → `docker run --rm -i ... ghcr.io/spkane/freecad-robust-mcp` (containerized stdio),
- `ros2` → `docker exec -i dronecad-ros2-jazzy …` (server lives inside the ROS container),
- `rosbags` → vendored clone (fork candidate, Phase 3),
- `memory` → `npx -y @shodh/memory-mcp` (stdio) + optional REST `:3030`.

**Consequences.** Works with how MCP actually works today (Claude Code / Cursor / other stdio clients). Phase 3 validates each server with a real `tools/list` call and records evidence in `REPORT.md`. If a non-stdio mode appears for a server (e.g. HTTP), a compose service can be added without breaking the registry.

---

## Current limits (2026-09-18)

- Phase 1 runtime images not built yet: compose references the official `ros:jazzy` image; the multi-stage Dockerfile with Gazebo/`ros_gz`/`ros2_control`/MoveIt 2 lands in Phase 1.
- FreeCAD is **not installed** on the host (audited); the `freecad` MCP entry relies on the Dockerized server.
- Kimi Code does not appear to read `.mcp.json` natively (`kimi --help` shows no MCP flag) — per-client registration is a Phase 3 item; Claude Code/Cursor read `.mcp.json` as-is.
- CPU-bound RTF is unmeasured; Gazebo performance targets are provisional until Phase 2.
- `docs/`, `README` and `REPORT` are bilingual: when editing one language, update the other.
