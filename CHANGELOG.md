# Changelog — DroneCAD

Toutes les modifications notables de ce projet sont documentées ici.
Format : [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/) · Versioning : [SemVer](https://semver.org/lang/fr/) · Horodatage ISO 8601 (fuseau local).
Les releases sont *delivery-gated* et **full-auto** : gérées par `.harness/scripts/release-check.py` (déclaré le 2026-09-18, mode `full-auto`).

## [Unreleased]

### Added

- **Phase 1** — image `dronecad/ros2-jazzy:0.1.0` multi-étapes (base : ROS 2 Jazzy + Gazebo Harmonic 8.15.0, `ros_gz` 1.0.24, `ros2_control` 4.48.0, MoveIt 2 2.12.4, `gz_ros2_control` 1.2.20 ; mcp : serveur `wise-vision/ros2_mcp` tag `2606` vendoré, venv **python système 3.12** avec assertion de build ; runtime : non-root uid 1000) ; conteneurs démarrés non-root, **démarrage de pile 3 s** ; pont FreeCAD natif `robust-mcp` v0.6.2 installé côté hôte.
- **Phase 2** — paquets ROS 2 `humanoid_description` (humanoïde 28 DoF, inerties calculées, capteurs RGB-D/IMU/contacts, transmissions `ros2_control`), `humanoid_gazebo` (mondes sol plat + obstacles, pont `ros_gz_bridge`, launch) et `humanoid_control` (contrôleurs position + effort, test de squat) : **robot debout ≥ 10 s simulées vérifié** (z = 1,065 m, roll/pitch ≈ 0, RTF 0,50 sans caméra) ; **squat suivi 0,031 rad** (seuil 0,25) ; 11/11 tests URDF (dont `check_urdf`).
- **Phase 3 (noyau)** — `agent/agent_loop.py` (allowlist par phase, timeout par appel, journal JSONL à corrélation, maximum 3 itérations), `agent/mcp_stdio.py` (client MCP stdio JSON-RPC 2.0 maison, diagnostic stderr, PATHEXT), 7 tests de garde-fous ; preuves `tools/list` réelles : **blender 31, ros2 20, memory 38** (`docs/mcp-tools-verified.md`).
- CI : tests URDF structurels (xacro en venv éphémère) + tests des garde-fous agentiques ajoutés au job `validate`.

## [v0.1.0] - 2026-09-18

- Scaffold initial : `README.md` bilingue EN/FR-CA, `ARCHITECTURE.md` (ADR 0001–0006), `AGENTS.md`, `REPORT.md`, brief fondateur `PROMPT_KIMI_CODE.md`.
- `docker-compose.yml` — squelette sécurisé (services non-root, réseau `agentnet`, ports liés à `127.0.0.1`, pas de `privileged`).
- `.mcp.json` — registre des 5 serveurs MCP (Blender, FreeCAD, ROS 2, rosbags, mémoire) + journal des invocations vérifiées.
- CI GitHub Actions : validation compose/JSON/YAML + `scripts/validate_stack.py` (ports publics, privileged, secrets) — action épinglée par SHA.
- Phase 0 exécutée : sondes matérielles réelles (RTX 4070 Ti SUPER 16376 MiB ; 31,7 Go RAM ; Docker 29.7.2/WSL2 ; Ollama 0.34.0), audit des dépôts de référence et des tags Ollama (verdicts adopt/fork/inspiration dans `README.md`).
- Modèle local retenu : `gpt-oss:20b` (14 Go, MXFP4) — `devstral:22b` inexistant au registre, `qwen3-coder-next` = 52 Go (hors 16 Go), `devstral-small-2:24b` = 15 Go (marge KV insuffisante). Détails : `docs/phase-0-hardware.md`, ADR-0002.
- Phase 0 terminée : banc officiel `gpt-oss:20b` → **115,44 tok/s** (eval, 1 189 tokens) / 222,96 tok/s (prefill), **100 % GPU** à contexte 8192, 1 463 Mio de VRAM libres ; contournement du crash amont ollama (#17380/#18522, `cuda_v13`/MXFP4) via serveur Ollama dédié `:11499` — ADR-0007 + `scripts/start-ollama-gptoss.ps1`.

### Fixed

- CI : le job `secret-scan` (gitleaks) peut lire les commits de PR (`pull-requests: read`) — le 403 « Resource not accessible by integration » est corrigé.
