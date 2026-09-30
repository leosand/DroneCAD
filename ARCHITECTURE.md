# Architecture decisions

Architecture Decision Records (ADR) for DroneCAD. Each record follows: context, decision, consequences, alternatives. For a short overview see [docs/OVERVIEW.md](docs/OVERVIEW.md).

## ADR-0001: Windows host with Docker Desktop (WSL2)

Status: accepted.

- Context: the original brief assumed a Linux host. The reference machine runs Windows with an NVIDIA RTX 4070 Ti SUPER (16 GB), Docker in Linux container mode (WSL2 backend) and Ollama.
- Decision: Blender and FreeCAD run natively on the host (GUI and GPU). ROS 2 Jazzy, Gazebo Harmonic and the ROS MCP server run in Linux containers.
- Consequences: Gazebo validation is headless. VRAM is shared between host applications and the local model, so avoid heavy GPU work in parallel. The CPU, not the GPU, is the main risk for a real-time factor of 1.
- Alternatives rejected: reinstalling on native Linux; a WSL2-native ROS install without Docker (the design requires compose isolation).

## ADR-0002: Local agentic model `gpt-oss:20b`

Status: accepted.

- Context: the model must be fully resident in 16 GB of VRAM with room for the KV cache, run at 40 tokens per second or more, and keep at least 1.5 GB free.
- Audit of candidates:

| Candidate | Finding | Verdict |
|---|---|---|
| `devstral:22b` | Tag does not exist | Rejected |
| `devstral-small-2:24b` | 15 GB, no KV-cache margin | Rejected |
| `qwen3-coder-next` | 52 GB, does not fit | Rejected |
| `gpt-oss:20b` | 14 GB (MXFP4), 128K context, tool calling | Adopted |
| `gemma4:12b` | 7.6 GB | Kept as fallback |

- Decision: `gpt-oss:20b`. Measured 115.44 tokens per second, 100% GPU residency at context 8192.
- Alternatives rejected: a 30B MoE model with CPU offload (breaks full residency); cloud models (breaks the local-first requirement).

## ADR-0003: Gazebo Harmonic now, MuJoCo later for reinforcement learning

Status: accepted.

- Decision: Gazebo Harmonic (`gz-sim8`, long-term support) with the canonical `gazebosim/ros_gz` bridge is the simulator for phases 1 to 5. MuJoCo is recommended as a future phase for locomotion reinforcement learning. Controllers trained there would be re-validated in Gazebo.
- Consequences: the URDF must stay MJCF-compatible (single root, convex collision primitives). A 4-core CPU may not sustain a real-time factor of 1 with the camera and IMU enabled; measured 0.60 with them and 0.50 without.

## ADR-0004: Geometry chain and URDF export

Status: accepted.

- Context: Phobos, the usual Blender URDF exporter, is tested on Blender 3.3 LTS and has open breakage on Blender 4.2 and later. The reference host runs Blender 5.2.
- Decision: Blender stays on the host. URDF export must not depend on Phobos. The primary path is a deterministic `bpy` export script driven by a versioned master `.blend` file.
- Consequences: the reproducible export requirement is kept and the Phobos dependency is removed.

## ADR-0005: Security and isolation baseline

Status: accepted.

- Decision: non-root users in every container; no `privileged: true` (it would need its own ADR); published ports bound to `127.0.0.1` only; a named internal network `agentnet`; secrets only through environment variables or secret stores; GitHub Actions pinned by SHA; `scripts/validate_stack.py` enforces these rules locally and in CI. The agent loop adds a per-phase tool allowlist, per-call timeouts and a structured JSON journal with correlation IDs.
- Rationale: least privilege is enforced mechanically, not by convention.

## ADR-0006: MCP servers are spawned by the client

Status: accepted.

- Context: the ROS 2, FreeCAD and rosbags MCP servers use stdio. They are started by the MCP client, not long-running daemons.
- Decision: `docker-compose.yml` holds runtime services only (`ros2-jazzy`, `shodh-memory`). The five MCP servers are registered in `.mcp.json` and spawned by the client. See [docs/mcp-tools-verified.md](docs/mcp-tools-verified.md).
- Consequences: works with Claude Code and Cursor as is. Kimi Code does not read `.mcp.json`, so its entries must be copied by hand.

## ADR-0007: Dedicated Ollama server for `gpt-oss:20b`

Status: accepted.

- Context: on the reference machine (Windows, Ada GPU, Ollama 0.34), loading `gpt-oss:20b` with flash attention, an 8-bit KV cache and the `cuda_v13` backend crashes the runner at initialization (`CUDA error: shared object initialization failed` in `MUL_MAT`). This matches open upstream Ollama issues #17380 and #18522. Other models run fine.
- Six isolated attempts showed that only `cuda_v12` with flash attention off and an f16 KV cache loads. Reducing the context to 8192 gives full GPU residency.
- Decision: serve the agentic model from a dedicated Ollama instance on `127.0.0.1:11499` with `OLLAMA_LLM_LIBRARY=cuda_v12`, `OLLAMA_FLASH_ATTENTION=0`, `OLLAMA_KV_CACHE_TYPE=f16` and `OLLAMA_CONTEXT_LENGTH=8192`. It is started by `scripts/start-ollama-gptoss.ps1`. Other Ollama servers and their global settings are untouched.
- Consequences: DroneCAD components target port 11499. Retire the dedicated server once upstream fixes the crash and the model is re-benchmarked. The 1,463 MiB of free VRAM is about 5% under the strict 1.5 GiB target but stable, because the KV cache is preallocated. `gemma4:12b` remains the strictly compliant fallback.
- Alternatives rejected: changing the global environment for every model; waiting for the upstream fix; downgrading the model.

## ADR-0008: Vendored `mcp-rosbags` with a compatibility wrapper

Status: accepted.

- Context: the upstream `mcp-rosbags` server is stale and cannot read the bag format written by ROS 2 Jazzy (version 9).
- Decision: keep it as a pinned git submodule under `vendor/mcp-rosbags` and run it through a small compatibility wrapper that uses a modern `rosbags` release and shims the CDR (de)serialization functions, with `mcp<2`. Forking stays an option if the wrapper stops being enough.
- Consequences: the server reads real Jazzy bags (11,526 messages verified). Changing the submodule URL is enough to switch to a fork.

## Current limits

- Real-time factor of 1 is not reached with the camera enabled (0.60 measured).
- The headless CI world has no rendering plugin.
- Kimi Code needs manual MCP registration.
- Results come from simulation only.
