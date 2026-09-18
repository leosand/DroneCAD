# AGENTS.md — DroneCAD

> EN: Entry point for AI agents working in this repository. / FR : Point d'entrée pour les agents IA travaillant dans ce dépôt.

## Contexte

DroneCAD est la **stack de prototypage humanoïde agentique** (Blender + FreeCAD + ROS 2 Jazzy + Gazebo Harmonic + MCP),
pilotée par un modèle local (`gpt-oss:20b`) sur une RTX 4070 Ti SUPER 16 Go, hôte Windows + Docker Desktop (WSL2).

- Brief fondateur (contrat) : `PROMPT_KIMI_CODE.md` — à lire avant toute contribution.
- État réel des phases et écarts documentés : `REPORT.md` (**source de vérité de l'avancement**).
- Décisions d'architecture : `ARCHITECTURE.md` (ADR 0001–0006).

## Règles de travail

1. **Bilingue** — commentaires de code et fichiers de configuration critiques : `// EN: ... / FR : ...`.
2. **Python 3.12**, type hints stricts pour la couche agentique ; **TypeScript strict** si une UI d'orchestration est ajoutée.
3. **Sécurité d'abord** — conteneurs non-root, aucun port publié hors `127.0.0.1`, aucun secret codé en dur, jamais de `privileged: true` sans ADR.
4. **Pas de TODO silencieux** — tout élément reporté ou écarté est tracé dans `REPORT.md` (section « En attente / blocages »).
5. **Versioning harness** — SemVer + `CHANGELOG.md` (`[Unreleased]` alimentée) ; releases **full-auto** gérées par `.harness/scripts/release-check.py` du harness parent (`E:/Mes apps`). Ne pas tagger manuellement.
6. **Modèle local** — `gpt-oss:20b` (voir ADR-0002) ; ne pas présumer d'un autre modèle sans mise à jour de l'ADR.
7. **Sources de vérité** — code > tests > `REPORT.md` > `PROMPT_KIMI_CODE.md`.

## Commandes clés

```bash
docker compose config -q            # validation du compose / compose validation
python scripts/validate_stack.py    # ports publics, privileged, secrets, .mcp.json
docker compose up -d ros2-jazzy     # Phase 1 : conteneur ROS 2 / Gazebo
```

## Périmètre agentique (rappel du brief)

- Les serveurs MCP **stdio** (blender, freecad, ros2, rosbags, memory) sont lancés par le client agent — voir ADR-0006 et `.mcp.json`.
- Allowlist d'outils par phase, timeout par appel, journal JSON à correlation ID : obligatoires dans `agent_loop.py` (Phase 3).
