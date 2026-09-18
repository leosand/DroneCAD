# REPORT.md — DroneCAD : état vérifié & auto-évaluation

> Dernière mise à jour : **2026-09-18** (America/Toronto, UTC-4).
> EN: single source of truth for progress, evidence and deviations from the founding brief. / FR-CA : source de vérité de l'avancement — **aucun TODO silencieux**.

## Portée de la session d'amorçage (2026-09-18)

Création du projet (repo GitHub privé `leosand/DroneCAD` + dossier local `E:/Mes apps/DroneCAD`), exécution de la **Phase 0** du brief (détection matérielle → audit des dépendances → choix et banc du modèle local) et livraison du **squelette sécurisé** (compose, registre MCP, CI, ADR). Les phases 1→5 se poursuivent sur cette base (voir « En attente »).

## Phase 0 — Matériel & modèle local — ✅ exécutée

- Sondes : RTX 4070 Ti SUPER 16 376 MiB (pilote 610.88) · Xeon W-2123 4c/8t · 31,7 Go RAM · Docker 29.7.2/WSL2 · Ollama 0.34.0 · Python 3.12.10 · Blender 5.2 (hôte).
- Décision : **`gpt-oss:20b`** (14 Go, MXFP4) — `devstral:22b` inexistant, `devstral-small-2:24b` (15 Go) sans marge KV, `qwen3-coder-next` = 52 Go. Détails + preuves : `docs/phase-0-hardware.md`, ADR-0002.

<!-- BENCH -->

<!-- VRAM -->

## Phase 5 — Liste de contrôle du brief (auto-vérification)

| # | Critère | État | Preuve / note |
|---|---|---|---|
| 1 | Modèle local chargé, résident GPU, tok/s rapportés, alternatives documentées | ⏳ banc en cours | pull en cours (~13 Go) ; alternatives documentées (ADR-0002) |
| 2 | `docker compose config` valide ; tous conteneurs non-root démarrés | 🟡 config validée | `docker compose config` OK + `validate_stack.py` OK ; démarrage réel des conteneurs = Phase 1 (images) |
| 3 | `.mcp.json` : chaque serveur répond à un appel `tools/list` réel | ⏳ Phase 3 | registre livré (5 serveurs) ; épreuves `tools/list` requises par serveur |
| 4 | Robot humanoïde debout ≥ 10 s dans Gazebo (log `joint_states`) | ⏳ Phase 2 | paquets ROS 2 à créer |
| 5 | Boucle agentique complète (STEP, BLEND, URDF, ROS bag, diagnostic) | ⏳ Phase 3 | `agent_loop.py` + garde-fous à écrire |
| 6 | CI verte sur la branche `feature/initial-stack` | ⏳ en cours | `ci.yml` livré (actions épinglées par SHA) ; vérifié après push |
| 7 | Aucun secret, aucun port exposé publiquement, scan Trivy propre | 🟡 partiel | `scripts/validate_stack.py` OK (loopback, non-root, pas de privileged) ; Trivy = Phase 4 |
| 8 | Table des dépôts GitHub audités (adopt/fork/inspiration) | ✅ | `README.md` § *Reference repositories audited* (audit réel 2026-09-18) |

## Écarts au brief fondateur (tracés, jamais silencieux)

1. **Hôte Windows** (le brief suppose Linux : `free -h`, xvfb, conteneurs GUI) → ADR-0001 : sondes PowerShell équivalentes, ROS 2/Gazebo en conteneurs WSL2, Blender/FreeCAD sur l'hôte.
2. **`devstral:22b` n'existe pas** au registre Ollama ; `qwen3-coder-next` = 52 Go (≠ ~16 Go du brief) → application de la règle de repli du brief (niveau 2 : `gpt-oss:20b`), ADR-0002.
3. **`ros2/ros_gz` n'existe pas** → dépôt canonique `gazebosim/ros_gz` (README).
4. **`spkane/freecad-robust-mcp`** : le dépôt n'existe pas sous ce nom ; l'image `ghcr.io/spkane/freecad-robust-mcp` existe ; dépôt canonique `spkane/freecad-addon-robust-mcp-server` (MIT, actif).
5. **Phobos** inutilisable sur Blender ≥ 4.2 (hôte = 5.2) → export URDF par script `bpy` reproductible (ADR-0004).
6. **Transport MCP** : les serveurs `ros2-mcp`, `freecad-mcp`, `mcp-rosbags` sont **stdio** (lancés par le client), pas des démons → le compose ne contient que les services d'exécution (ADR-0006).
7. **Kimi Code** ne lit pas `.mcp.json` nativement (`kimi --help` sans MCP) → enregistrement par client prévu en Phase 3 ; Claude Code/Cursor lisent le format tel quel.

## Validations exécutées (preuves)

<!-- VALIDATIONS -->

## En attente / prochaines actions (aucun TODO silencieux)

- **Phase 0 (fin)** : banc `gpt-oss:20b` (tok/s) + marge VRAM → sections ci-dessus (pull en cours au moment d'écrire).
- **Phase 1** : Dockerfile multi-étapes `ros2-jazzy` (Gazebo Harmonic + `ros_gz` + `ros2_control` + MoveIt 2), utilisateur non-root `ros` (uid 1000), build + `docker compose up`, contrôle `id -u` non-root, mesures de démarrage (< 90 s visé).
- **Phase 2** : paquets ROS 2 `humanoid_description` / `humanoid_gazebo` / `humanoid_control` ; script d'export URDF depuis `.blend` maître ; pytest URDF (check_urdf, inerties, liens orphelins) ; test Gazebo headless debout ≥ 10 s (+ mesures RTF, cible 1/1).
- **Phase 3** : `agent_loop.py` (allowlist par phase, timeout par appel, journal JSON à correlation ID, boucle max 3) ; clone vendor `mcp-rosbags` (candidat fork — dépôt stale) ; épreuves `tools/list` par serveur MCP ; enregistrement Kimi/Cursor.
- **Phase 4** : CI complète (colcon, xvfb/Gazebo headless, Trivy image), image multi-étapes taguée v0.1.0.
- **Release v0.1.0** : mode **full-auto** déclaré (rules.yaml `declared_modes`) → `release-check.py` promeut `[Unreleased]`, tague et publie en pre-release dès que CI verte + commits qualifiés (voir CHANGELOG).

## Journal de session (amorçage)

| Heure (ET) | Événement |
|---|---|
| 17:43 | Sondes matérielles + harness (skill `harness-meta`, vault-first, règle 9 : mode de release demandé → `full-auto`) |
| 17:45 | Audit en ligne des dépôts de référence + tags Ollama (vérification réelle, verdicts) |
| 17:50 | Création du dossier local + `git init` ; pull `gpt-oss:20b` en arrière-plan |
| 17:55 | Scaffold : README/ADR/AGENTS/CHANGELOG/PROMPT, compose sécurisé, `.mcp.json`, CI, `validate_stack.py` |
