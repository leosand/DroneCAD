# REPORT.md — DroneCAD : état vérifié & auto-évaluation

> Dernière mise à jour : **2026-09-19** (America/Toronto).
> EN: single source of truth for progress, evidence and deviations from the founding brief. / FR-CA : source de vérité de l'avancement — **aucun TODO silencieux**.

## Avancement global

| Phase | État | Preuves clés |
|---|---|---|
| 0. Matériel & modèle local | ✅ | `gpt-oss:20b` — 115,44 tok/s, 100 % GPU ctx 8192, serveur dédié `:11499` (ADR-0002/0007, `docs/phase-0-hardware.md`) |
| 1. Isolation & orchestration | ✅ | image multi-étapes `dronecad/ros2-jazzy:0.1.0` (Gazebo Harmonic **8.15.0**, `ros_gz` 1.0.24, `ros2_control` 4.48.0, MoveIt 2 **2.12.4**, `gz_ros2_control` **1.2.20**, rviz2 ; serveur `ros2_mcp` tag `2606` vendoré dans `/opt/ros2-mcp`) ; conteneurs non-root **uid 1000** ; **démarrage de pile 3 s** ; pont FreeCAD `robust-mcp` v0.6.2 installé côté hôte (activation RPC = action utilisateur, cf. Phase 3) |
| 2. Chaîne de conception humanoïde | ✅ | 3 paquets ROS 2 ; **debout ≥ 10 s simulées : z = 1,065 m, roll/pitch ≈ 0** ; **squat : erreur max 0,031 rad** (seuil 0,25) ; **11/11 tests URDF** (dont `check_urdf`) ; colcon 18,8 s ; **RTF physics 0,50** (sans caméra — limite CPU, cf. écart 11) |
| 3. Boucle agentique MCP | 🟡 noyau livré | garde-fous + client stdio + 7 tests verts ; `tools/list` réels : **blender 31 ✅, memory 38 ✅** ; `ros2` en retest post-correctif ; `freecad` (RPC utilisateur) et `rosbags` (vendor) en attente ; boucle bout-en-bout non exécutée |
| 4. CI/CD & qualité | 🟡 minimal | `validate` (compose + stack + URDF + garde-fous) et `secret-scan` verts ; colcon/Gazebo-headless/Trivy en CI = à ajouter |
| 5. Vérification | 🟡 6/8 | tableau ci-dessous |

## Phase 0 — Matériel & modèle local — ✅ TERMINÉE

- Sondes : RTX 4070 Ti SUPER 16 376 Mio (pilote 610.88) · Xeon W-2123 4c/8t · 31,7 Go RAM · Docker 29.7.2/WSL2 · Ollama 0.34.0 · Python 3.12.10 · Blender 5.2 (hôte) · FreeCAD **1.1.3** (hôte, user-local — la première sonde ne couvrait que `Program Files`, corrigé).
- Décision : **`gpt-oss:20b`** — `devstral:22b` inexistant, `devstral-small-2:24b` (15 Go) sans marge KV, `qwen3-coder-next` = 52 Go. (ADR-0002)
- **Incident runtime résolu** : crash backend `cuda_v13`/MXFP4 (bug amont ollama #17380/#18522) → serveur dédié `:11499` (`cuda_v12`+FA=0+KV f16+ctx 8192), principal `:11480` intact (ADR-0007, `scripts/start-ollama-gptoss.ps1`).
- Banc : **115,44 tok/s** (eval, 1 189 tokens) · 222,96 (prefill) · `ollama ps` = 100 % GPU · 1 463 Mio libres (stable, documentation en `docs/phase-0-hardware.md`).

## Phase 1 — Isolation & orchestration — ✅

- **`docker/ros2-jazzy/Dockerfile` multi-étapes** : `base` (ROS 2 Jazzy + Gazebo Harmonic + `ros_gz` + `ros2_control` + contrôleurs + MoveIt 2 + rviz2 + `liburdfdom-tools`), `mcp` (serveur `wise-vision/ros2_mcp` tag `2606` vendoré, venv **python système**), `runtime` (non-root uid 1000 réutilisant l'utilisateur `ubuntu` de l'image ROS — un second `useradd -u 1000` échoue, vérifié).
- **Correctifs de build documentés** : uid 1000 déjà pris dans `ros:jazzy` ; `$(find)` interdit au xacro standalone (chemin des contrôleurs injecté par le launch) ; venv uv sous `/root` inaccessible au non-root → `UV_PYTHON_DOWNLOADS=never` + `--python /usr/bin/python3`.
- Conteneurs : `ros2-jazzy` (Up, uid 1000) + `shodh-memory` (healthy, `127.0.0.1:3030`) ; **démarrage mesuré : 3 s** (cible brief < 90 s ✅).
- **FreeCAD natif** : workbench `robust-mcp` v0.6.2 cloné dans `%APPDATA%\FreeCAD\v1-1\Mod\freecad-robust-mcp` ; `.mcp.json` cible l'installation locale (`uvx --from freecad-robust-mcp --with 'mcp<2' freecad-mcp`, mode xmlrpc) ; **activation du serveur RPC (:9875) = action utilisateur** (redémarrer FreeCAD → workbench « Robust MCP Bridge » → Start).

## Phase 2 — Chaîne de conception humanoïde — ✅

- **Paquets** (`ws/src/`) : `humanoid_description` (28 DoF : torse 2 + nuque 2 + bras 6×2 + jambes 6×2 ; inerties calculées des volumes, limites/efforts, capteurs tête RGB-D + IMU, contacts plantaires, transmissions `ros2_control` position+effort) · `humanoid_gazebo` (mondes `flat_ground.sdf` + `obstacles.sdf`, pont `ros_gz_bridge` — `/clock`, `/imu`, `/camera*`, `/cmd_vel` ; `/joint_states` fourni par ros2_control) · `humanoid_control` (contrôleurs groupe position + effort, `scripts/squat_test.py`).
- **Validation** : `colcon build` 3 paquets (18,8 s) ; tests URDF **11/11 en conteneur** (dont `check_urdf`) ; tests locaux 10+1 skip+7 garde-fous en pseudo-venv CI.
- **Test d'acceptation du brief — robot debout ≥ 10 s simulées** : ✅ `z = 1,065 m, roll = 0,000, pitch = −0,000` (échantillonnage `/model/humanoid/pose`, temps simulé via `/clock`).
- **Squat** (consignes sinusoïdales 8 s simulées) : ✅ erreur max genou **0,031 rad** (seuil 0,25).
- **Correctifs découverts et documentés** : `PosePublisher` doit être attaché au **modèle** (pas au monde — erreur `PosePublisher.cc:194` vérifiée) ; contrôleurs activés à t+3 s pour réduire la fenêtre non-actuée ; RTF physics **0,50** (sans caméra).

## Phase 3 — Boucle agentique MCP — 🟡 noyau livré

- `agent/agent_loop.py` : allowlist par phase, timeout par appel, journal JSONL à **correlation ID par itération**, boucle bornée **max 3 itérations** (garde-fous explicites du brief) ; `agent/mcp_stdio.py` : client MCP stdio JSON-RPC 2.0 maison (zéro dépendance, diagnostic stderr, résolution PATHEXT Windows) ; `agent/tool_allowlist.json` figé sur les **noms d'outils réels** vérifiés ; 7 tests verts (`agent/tests/test_guards.py`).
- **`tools/list` réels** (voir `docs/mcp-tools-verified.md`) : **blender ✅ 31 outils**, **memory ✅ 38 outils** (v0.2.0) ; `ros2` : retest après correctif venv ; `freecad` : en attente du RPC utilisateur ; `rosbags` : clone vendor + décision fork à faire.
- **Boucle bout-en-bout (STEP/BLEND/bag/diagnostic)** : non exécutée — dépend des serveurs ci-dessus + agents.

## Phase 5 — Liste de contrôle du brief (auto-vérification)

| # | Critère | État | Preuve / note |
|---|---|---|---|
| 1 | Modèle local chargé, résident GPU, tok/s rapportés, alternatives documentées | ✅ | 115,44 tok/s, 100 % GPU ctx 8192, 1 463 Mio libres, ADR-0002/0007 |
| 2 | `docker compose config` valide ; tous conteneurs non-root démarrés | ✅ | config OK ; 2 services Up ; `id -u` = 1000 ; port 3030 loopback ; démarrage 3 s |
| 3 | `.mcp.json` : chaque serveur répond à un appel `tools/list` réel | 🟡 2/5 | blender 31 ✅, memory 38 ✅ ; ros2 (retest) ; freecad (RPC utilisateur) ; rosbags (vendor) |
| 4 | Robot humanoïde debout ≥ 10 s dans Gazebo (log `joint_states`) | ✅ | z=1,065 m, roll/pitch ≈ 0, ≥ 10 s simulées — test `test_stand.py` + `/joint_states` via ros2_control |
| 5 | Boucle agentique complète (STEP, BLEND, URDF, ROS bag, diagnostic) | ⏳ | noyau + garde-fous livrés ; exécution bout-en-bout après activation freecad/blender/rosbags |
| 6 | CI verte sur la branche `feature/initial-stack` | ✅ | bootstrap : runs `35401837823`/`35401841242` ; CI `main` verte à chaque commit (`validate` + `secret-scan` + URDF + garde-fous) |
| 7 | Aucun secret, aucun port exposé publiquement, scan Trivy propre | 🟡 | `validate_stack.py` OK ; gitleaks vert ; secret scanning GitHub indisponible (GHAS, 422) → compensé ; Trivy = Phase 4 |
| 8 | Table des dépôts GitHub audités (adopt/fork/inspiration) | ✅ | `README.md` § *Reference repositories audited* (audit en ligne 2026-09-18) |

## Écarts au brief fondateur (tracés, jamais silencieux)

1. **Hôte Windows** (le brief suppose Linux) → ADR-0001 (sondes PowerShell, conteneurs WSL2, Blender/FreeCAD hôte).
2. **`devstral:22b` inexistant** ; `qwen3-coder-next` = 52 Go → repli niveau 2 `gpt-oss:20b` (ADR-0002).
3. **Crash amont gpt-oss** (cuda_v13/MXFP4, ollama #17380/#18522) → serveur dédié (ADR-0007) ; marge VRAM 1 463 Mio (préalloué, documenté).
4. **`ros2/ros_gz` n'existe pas** → canonique `gazebosim/ros_gz`.
5. **`spkane/freecad-robust-mcp`** : dépôt inexistant ; image ghcr valide ; dépôt canonique `spkane/freecad-addon-robust-mcp-server` ; client PyPI exige le pin `mcp<2` (bug de métadonnées amont vérifié).
6. **Phobos** inutilisable sur Blender ≥ 4.2 (hôte = 5.2) → export URDF par générateur paramétrique (ADR-0004) ; addon Blender `mcp-for-blender` (Blender 5.x non vérifié par son amont) : installation/enable = action utilisateur.
7. **Transport MCP stdio** : lancés par le client (`.mcp.json`), pas des services compose (ADR-0006).
8. **Kimi Code** ne lit pas `.mcp.json` nativement → enregistrement par client (Phase 3).
9. **Secret scanning GitHub** indisponible (GHAS) → gitleaks CI (compensation).
10. **Pipeline Hermes cassé depuis le 2026-09-16** (hors DroneCAD) → vault enregistré via `sync_projects.py` (gate neutralisé en mémoire, one-off) ; **revue humaine requise**, aucun correctif appliqué.
11. **Caméra/RTF** : tests headless avec `enable_camera:=false` (rendu GPU non exposé au conteneur) ; RTF physics mesuré **0,50** (limite CPU du Xeon 4 cœurs) ; RTF 1/1 caméra+IMU activés → pistes Phase 4 (rendu WSLg/GPU passthrough, réduction du pas physique, tâches CPU dédiées).

## Validations exécutées (preuves)

```text
compose : config OK · 2 services Up (shodh healthy) · id -u = 1000 (les deux) · port 3030 loopback · démarrage 3 s
image   : ros:jazzy + Gazebo 8.15.0 + ros_gz 1.0.24 + ros2_control 4.48.0 + MoveIt 2.12.4 + gz_ros2_control 1.2.20
build   : colcon 3 paquets OK (18,8 s)
tests   : URDF 11/11 (check_urdf inclus) · garde-fous agent 7/7 · CI verte (dernier run 35408063292)
gazebo  : debout ≥ 10 s simulées → z=1,065 m, roll=0,000, pitch=-0,000 · squat erreur max 0,031 rad · RTF 0.50
mcp     : tools/list blender=31, memory=38 (client stdio maison) ; ros2 en retest ; freecad=attente RPC ; rosbags=attente vendor
ollama  : gpt-oss:20b 100% GPU ctx 8192, eval 115,44 tok/s, prefill 222,96 tok/s, 1 463 Mio libres
```

## En attente / prochaines actions (aucun TODO silencieux)

- **Utilisateur** : (a) redémarrer FreeCAD → workbench « Robust MCP Bridge » → Start server (:9875) ; (b) si souhaité, `uvx mcp-for-blender install-addon` + activer l'addon dans Blender 5.2 (compat non vérifiée par l'amont).
- **Phase 3 (suite)** : retest `tools/list ros2` (correctif venv venant d'être appliqué) ; clone vendor `mcp-rosbags` + décision fork ; compléter l'allowlist freecad/ros2/rosbags depuis les listes réelles ; exécuter la boucle bout-en-bout (STEP → BLEND → URDF → bag → diagnostic).
- **Phase 4** : jobs CI colcon + Gazebo headless (xvfb) + Trivy ; mesures RTF caméra+IMU (GPU passthrough) ; réduction du pas physique si besoin.
- **Release** : full-auto — le CHANGELOG porte désormais une section `[Unreleased]` (phases 1-3) ; la tâche quotidienne `release-check --all --auto` coupera la prochaine version (pre-release) dès que la CI est verte.
- **Vault** : fiche projet + session à mettre à jour (fait dans la session courante) ; connaissance gpt-oss en brouillon (promotion après relecture humaine).

## Journal (suite de session, 2026-09-18 soir → 2026-09-19)

| Heure (ET) | Événement |
|---|---|
| ~19:20 | Corrections audit : FreeCAD 1.1.3 localisé (sonde Program Files incomplète), repo canonique `spkane/freecad-addon-robust-mcp-server` |
| ~19:25 | Phase 1 : Dockerfile multi-étapes écrit ; build #1 (échec uid 1000) → correctif → build #2 OK ; gz_ros2_control ajouté → build #3 OK |
| ~19:35 | FreeCAD : workbench `robust-mcp` v0.6.2 installé côté hôte ; `.mcp.json` recâblé (client pin `mcp<2`) |
| ~19:40 | Phase 2 : paquets description/gazebo/control écrits ; tests URDF locaux 10+1 ; CI URDF + garde-fous ajoutés |
| ~19:45 | Phase 3 : preuves `tools/list` blender (31) et memory (38) ; client rendu diagnosticable ; allowlist figée |
| ~23:45–00:05 | Conteneur recréé (uid 1000, gz 8.15.0) ; colcon OK ; **debout 10 s OK** (correctif PosePublisher modèle) ; squat 0,031 rad ; RTF 0.50 ; démarrage 3 s ; correctif venv uv → rebuild |
