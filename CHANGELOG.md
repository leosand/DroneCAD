# Changelog

All notable changes to this project are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versioning: [SemVer](https://semver.org/).

## [Unreleased]

### Added

- MIT `LICENSE`, `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, `CITATION.cff`, issue and pull request templates.
- Documentation rewritten in English: `README.md`, `ARCHITECTURE.md`, `docs/`.

## [0.3.0] - 2026-09-19

### Added

- Local cognitive memory works without any third-party key. `SHODH_API_KEYS` is a key you generate for your own `shodh-memory` server. It is documented in `.env.example`, injected by `docker-compose.yml` and expanded by `.mcp.json` as `SHODH_API_KEY`. Verified with real `memory_stats`, `remember` and `recall` calls (95% relevance).
- `docs/USAGE.md`: usage guide. `docs/TESTING.md`: six-level validation procedure.
- Phase 4 CI: `lint` (Ruff) and `container-tests` (colcon, URDF tests, Gazebo smoke test, headless standing test in the delivered image, Trivy scan of HIGH and CRITICAL fixable vulnerabilities). Actions are pinned by SHA.
- Headless camera verified: `/camera`, `/camera/image`, `/camera/depth_image` and `/camera/points` are published. Real-time factor 0.60 with camera and IMU.
- ADR-0008 for `mcp-rosbags`.

### Fixed

- MCP servers no longer read the repository `.env` (they start outside the repository), and `${VAR}` expansion uses the environment plus `.env`.
- A clear error is raised when an MCP executable is missing or a `${VAR}` in `.mcp.json` is undefined.
- Gazebo runs as user 1000. A user ID without a `/etc/passwd` entry silenced gz-transport in CI.
- Headless world without the OGRE2 rendering plugin (it hung on runners without a display).
- Robust robot spawn that waits for the Gazebo world service.
- Security bumps in the vendored virtual environment: pillow, cryptography, python-multipart and anyio (CVE-2026-63374).
- `agent/mcp_call.py` forces UTF-8 output on Windows consoles.
- Script executable bits recorded in Git.

## [0.2.0] - 2026-09-19

### Added

- Phase 1: multi-stage `ros2-jazzy` image with Gazebo Harmonic, MoveIt 2, `ros_gz`, `ros2_control` and the ROS 2 MCP server.
- Phase 2: humanoid ROS 2 packages (28 DoF): description, Gazebo and control. URDF checks in CI. Standing test for 10 simulated seconds and a squat test.
- Phase 3: five MCP servers verified with real `tools/list` and tool calls. Agent loop with per-phase allowlist, per-call timeout and JSONL journal. End-to-end bracket loop (`E2E_OK`).
- Native FreeCAD bridge (`freecad-robust-mcp`) and a vendored `mcp-rosbags` compatibility wrapper for Jazzy v9 bags.

## [0.1.0] - 2026-09-18

### Added

- Initial scaffold: documentation, ADR 0001 to 0006, secure `docker-compose.yml`, `.mcp.json` registry, CI validation, `scripts/validate_stack.py`, and gitleaks secret scanning.
- Phase 0: hardware probes, dependency audit and local model selection (`gpt-oss:20b`, 115.44 tokens per second, 100% GPU).
- ADR-0007: dedicated Ollama server (`scripts/start-ollama-gptoss.ps1`) to work around an upstream crash.
