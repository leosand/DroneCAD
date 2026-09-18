# Changelog — DroneCAD

Toutes les modifications notables de ce projet sont documentées ici.
Format : [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/) · Versioning : [SemVer](https://semver.org/lang/fr/) · Horodatage ISO 8601 (fuseau local).
Les releases sont *delivery-gated* et **full-auto** : gérées par `.harness/scripts/release-check.py` (déclaré le 2026-09-18, mode `full-auto`).

## [Unreleased]

### Added

- Scaffold initial : `README.md` bilingue EN/FR-CA, `ARCHITECTURE.md` (ADR 0001–0006), `AGENTS.md`, `REPORT.md`, brief fondateur `PROMPT_KIMI_CODE.md`.
- `docker-compose.yml` — squelette sécurisé (services non-root, réseau `agentnet`, ports liés à `127.0.0.1`, pas de `privileged`).
- `.mcp.json` — registre des 5 serveurs MCP (Blender, FreeCAD, ROS 2, rosbags, mémoire) + journal des invocations vérifiées.
- CI GitHub Actions : validation compose/JSON/YAML + `scripts/validate_stack.py` (ports publics, privileged, secrets) — action épinglée par SHA.
- Phase 0 exécutée : sondes matérielles réelles (RTX 4070 Ti SUPER 16376 MiB ; 31,7 Go RAM ; Docker 29.7.2/WSL2 ; Ollama 0.34.0), audit des dépôts de référence et des tags Ollama (verdicts adopt/fork/inspiration dans `README.md`).
- Modèle local retenu : `gpt-oss:20b` (14 Go, MXFP4) — `devstral:22b` inexistant au registre, `qwen3-coder-next` = 52 Go (hors 16 Go), `devstral-small-2:24b` = 15 Go (marge KV insuffisante). Détails : `docs/phase-0-hardware.md`, ADR-0002.
