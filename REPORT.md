# REPORT.md — DroneCAD : état vérifié & auto-évaluation

> Dernière mise à jour : **2026-09-19** (America/Toronto).
> EN: single source of truth for progress, evidence and deviations from the founding brief. / FR-CA : source de vérité de l'avancement — **aucun TODO silencieux**.

## Avancement global

| Phase | État | Preuves clés |
|---|---|---|
| 0. Matériel & modèle local | ✅ | `gpt-oss:20b` — 115,44 tok/s, 100 % GPU ctx 8192, serveur dédié `:11499` (ADR-0002/0007) |
| 1. Isolation & orchestration | ✅ | image `dronecad/ros2-jazzy:0.1.0` (Gazebo Harmonic 8.15.0, `ros_gz`, `ros2_control`, MoveIt 2, `gz_ros2_control` ; `ros2_mcp` tag `2606` vendoré) ; conteneurs non-root uid 1000 ; démarrage 3 s |
| 2. Chaîne de conception humanoïde | ✅ | **debout ≥ 10 s simulées** (z = 1,065 m, roll/pitch ≈ 0) ; **squat 0,031 rad** ; 11/11 tests URDF (dont `check_urdf`) ; colcon 18,8 s ; RTF 0,50 (sans caméra) |
| 3. Boucle agentique MCP | 🟡 avancé | **5/5 serveurs MCP vérifiés** (`tools/list` + appels réels — `docs/mcp-tools-verified.md`) ; garde-fous + client stdio + `mcp_call.py` + 7 tests ; reste : exécution bout-en-bout |
| 4. CI/CD & qualité | 🟡 minimal | `validate` (compose + stack + URDF + garde-fous) et `secret-scan` verts ; colcon/Gazebo-headless/Trivy en CI = à ajouter |
| 5. Vérification | 🟡 6 ✅ / 1 🟡 / 1 ⏳ | tableau ci-dessous |

## Phase 0 — Matériel & modèle local — ✅ TERMINÉE

- Sondes : RTX 4070 Ti SUPER 16 376 Mio (pilote 610.88) · Xeon W-2123 4c/8t · 31,7 Go RAM · Docker 29.7.2/WSL2 · Ollama 0.34.0 · Python 3.12.10 · Blender 5.2 (hôte) · FreeCAD **1.1.3** (hôte, user-local).
- Décision : **`gpt-oss:20b`** — `devstral:22b` inexistant, `devstral-small-2:24b` (15 Go) sans marge KV, `qwen3-coder-next` = 52 Go (ADR-0002).
- **Incident runtime résolu** : crash backend `cuda_v13`/MXFP4 (ollama #17380/#18522) → serveur dédié `:11499` (`cuda_v12`+FA=0+KV f16+ctx 8192), principal `:11480` intact (ADR-0007, `scripts/start-ollama-gptoss.ps1`).
- Banc : **115,44 tok/s** (eval) · 222,96 (prefill) · 100 % GPU · 1 463 Mio libres.

## Phase 1 — Isolation & orchestration — ✅

- **`docker/ros2-jazzy/Dockerfile` multi-étapes** : `base` (ROS 2 Jazzy + Gazebo Harmonic + `ros_gz` + `ros2_control` + contrôleurs + MoveIt 2 + rviz2 + `liburdfdom-tools`), `mcp` (`wise-vision/ros2_mcp` tag `2606` vendoré, venv **python 3.12 système** + assertion de build), `runtime` (non-root uid 1000 — utilisateur `ubuntu` de l'image ROS réutilisé).
- **Correctifs de build documentés** : uid 1000 déjà pris ; `$(find)` interdit au xacro standalone ; venv uv sous `/root` inaccessible ; `.python-version` 3.10 du repo amont honoré par uv (incompatible rclpy 3.12) → supprimé au build.
- Conteneurs : `ros2-jazzy` (Up, uid 1000) + `shodh-memory` (healthy, `127.0.0.1:3030`) ; **démarrage mesuré : 3 s**.
- **FreeCAD natif** : workbench `robust-mcp` v0.6.2 (`%APPDATA%\FreeCAD\v1-1\Mod\freecad-robust-mcp`) ; **`AutoStart=True` posé par l'agent** (param `BaseApp/Preferences/Mod/RobustMCPBridge`) ; **FreeCAD relancé par l'agent** → bridge actif (XML-RPC 9875, socket 9877 — `SocketPort` déplacé pour libérer 9876) ; `.mcp.json` cible l'install locale (`uvx --from freecad-robust-mcp --with 'mcp<2' freecad-mcp`, mode xmlrpc).

## Phase 2 — Chaîne de conception humanoïde — ✅

- **Paquets** (`ws/src/`) : `humanoid_description` (28 DoF ; inerties calculées, limites/efforts, capteurs tête RGB-D + IMU, contacts plantaires, transmissions `ros2_control` position+effort) · `humanoid_gazebo` (mondes `flat_ground` + `obstacles`, pont `ros_gz_bridge` — `/clock`, `/imu`, `/camera*`, `/cmd_vel` ; `/joint_states` via ros2_control) · `humanoid_control` (contrôleurs position + effort, `scripts/squat_test.py`).
- **Validation** : colcon 3 paquets (18,8 s) ; tests URDF **11/11 en conteneur** (dont `check_urdf`) ; tests locaux + garde-fous en pseudo-venv CI.
- **Test d'acceptation du brief — debout ≥ 10 s simulées** : ✅ `z = 1,065 m, roll = 0,000, pitch = −0,000` (pose via `/model/humanoid/pose` — plugin `PosePublisher` attaché au **modèle**, temps simulé via `/clock`).
- **Squat** : ✅ erreur max genou **0,031 rad** (seuil 0,25).
- **RTF physics 0,50** sans caméra (limite CPU — écart 11).

## Phase 3 — Boucle agentique MCP — 🟡 avancé

- **Noyau livré** : `agent/agent_loop.py` (allowlist par phase, timeout par appel, journal JSONL à **correlation ID par itération**, max **3 itérations**) ; `agent/mcp_stdio.py` (client stdio JSON-RPC 2.0 maison — zéro dépendance, diagnostic stderr, PATHEXT Windows, expansion `${VAR}`) ; `agent/mcp_call.py` (appel direct d'un outil) ; 7 tests garde-fous verts.
- **5/5 serveurs MCP vérifiés** (détails et preuves : `docs/mcp-tools-verified.md`) :
  - `tools/list` : **blender 31 · freecad 83 · ros2 20 · rosbags 15 · memory 38** ;
  - **appels réels** : Blender **scène vivante** (`get_scene_info` : Cube/Light/Camera, protocole v7, addon v1.7) ; FreeCAD **1.1.3 vivant** (`get_freecad_version`, `gui_available 1`) ; ROS 2 **graphe vivant** (`ros2_topic_list`) ;
  - `memory` : appels 503 `AUTH_NOT_CONFIGURED` sans `SHODH_API_KEYS` (configuration utilisateur) — liste OK.
- **Environnement** : FreeCAD et Blender **relancés par l'agent** ; addon `blender_mcp` (mcp-for-blender) installé + activé + prefs sauvegardées (Blender 5.2, socket 9876) ; ports séparés (9875/9877 FreeCAD, 9876 Blender).
- **Pins découverts** : `mcp<2` (client freecad) ; `rosbags<0.10` (dépôt rosbags stale — candidat fork confirmé).
- **Reste** : exécution de la boucle bout-en-bout (STEP → BLEND → URDF → bag → diagnostic) ; enregistrement Kimi Code (ne lit pas `.mcp.json` nativement).

## Phase 5 — Liste de contrôle du brief (auto-vérification)

| # | Critère | État | Preuve / note |
|---|---|---|---|
| 1 | Modèle local chargé, résident GPU, tok/s rapportés, alternatives documentées | ✅ | 115,44 tok/s, 100 % GPU ctx 8192, 1 463 Mio libres, ADR-0002/0007 |
| 2 | `docker compose config` valide ; tous conteneurs non-root démarrés | ✅ | config OK ; 2 services Up ; `id -u` = 1000 ; port 3030 loopback ; démarrage 3 s |
| 3 | `.mcp.json` : chaque serveur répond à un appel `tools/list` réel | ✅ | **5/5** : blender 31, freecad 83, ros2 20, rosbags 15, memory 38 + appels d'outils réels (scène Blender, FreeCAD 1.1.3, topics ROS 2) |
| 4 | Robot humanoïde debout ≥ 10 s dans Gazebo (log `joint_states`) | ✅ | z=1,065 m, roll/pitch ≈ 0, ≥ 10 s simulées (`test_stand.py` + `/joint_states` ros2_control) |
| 5 | Boucle agentique complète (STEP, BLEND, URDF, ROS bag, diagnostic) | ⏳ | noyau + garde-fous + 5/5 serveurs prêts ; exécution bout-en-bout à lancer |
| 6 | CI verte sur la branche `feature/initial-stack` | ✅ | bootstrap `35401837823`/`35401841242` ; CI `main` verte à chaque commit (validate + secret-scan + URDF + garde-fous) |
| 7 | Aucun secret, aucun port exposé publiquement, scan Trivy propre | 🟡 | `validate_stack.py` OK ; gitleaks vert ; secret scanning GitHub indisponible (GHAS) → compensé ; Trivy = Phase 4 |
| 8 | Table des dépôts GitHub audités (adopt/fork/inspiration) | ✅ | `README.md` § *Reference repositories audited* |

## Écarts au brief fondateur (tracés, jamais silencieux)

1. **Hôte Windows** → ADR-0001 (conteneurs WSL2, Blender/FreeCAD hôte).
2. **`devstral:22b` inexistant** ; `qwen3-coder-next` = 52 Go → repli niveau 2 `gpt-oss:20b` (ADR-0002).
3. **Crash amont gpt-oss** (cuda_v13/MXFP4) → serveur dédié (ADR-0007) ; marge VRAM 1 463 Mio (préalloué, documenté).
4. **`ros2/ros_gz` n'existe pas** → canonique `gazebosim/ros_gz`.
5. **`spkane/freecad-robust-mcp`** : dépôt inexistant ; dépôt canonique `spkane/freecad-addon-robust-mcp-server` ; client PyPI exige `mcp<2`.
6. **Phobos** inutilisable sur Blender ≥ 4.2 → export URDF par générateur paramétrique (ADR-0004) ; addon Blender communautaire (`mcp-for-blender`) fonctionnel sur Blender 5.2 (vérifié : addon v1.7, protocole v7).
7. **Transport MCP stdio** : lancés par le client (`.mcp.json`), pas des services compose (ADR-0006).
8. **Kimi Code** ne lit pas `.mcp.json` nativement → enregistrement par client (à faire).
9. **Secret scanning GitHub** indisponible (GHAS) → gitleaks CI.
10. **Pipeline Hermes cassé depuis le 2026-09-16** (hors DroneCAD) → revue humaine requise, aucun correctif appliqué.
11. **Caméra/RTF** : tests headless caméra désactivée ; RTF physics **0,50** (limite CPU) ; pistes Phase 4.
12. **Spécificités Windows découvertes** : trampoline uv refusé une fois dans `%TEMP%` (AV/SAC probable, retry OK) ; collision de ports 9876 FreeCAD/Blender résolue (`SocketPort` 9877).

## Validations exécutées (preuves)

```text
compose : config OK · 2 services Up (shodh healthy) · id -u = 1000 · port 3030 loopback · démarrage 3 s
image   : Gazebo 8.15.0 · ros_gz 1.0.24 · ros2_control 4.48.0 · MoveIt 2.12.4 · gz_ros2_control 1.2.20
build   : colcon 3 paquets OK (18,8 s) · tests URDF 11/11 (check_urdf) · garde-fous 7/7 · CI verte
gazebo  : debout ≥ 10 s → z=1,065 m, roll=0,000, pitch=-0,000 · squat 0,031 rad · RTF 0.50
mcp     : tools/list 5/5 (blender 31, freecad 83, ros2 20, rosbags 15, memory 38)
          appels réels : blender get_scene_info (Cube/Light/Camera) · freecad get_freecad_version (1.1.3)
          ros2 ros2_topic_list (/parameter_events…) · memory : SHODH_API_KEYS requis pour les appels
ports   : 9875 XML-RPC FreeCAD (PID FreeCAD) · 9876 socket Blender addon · 9877 socket FreeCAD
ollama  : gpt-oss:20b 100% GPU ctx 8192, eval 115,44 tok/s, 1 463 Mio libres
releases: v0.1.0 (2026-09-18) + v0.2.0 (2026-09-19) — pre-releases vérifiées via gh release view
```

## En attente / prochaines actions (aucun TODO silencieux)

- **Phase 3 (suite)** : exécuter la boucle bout-en-bout (bracket FreeCAD → STEP → assemblage Blender → URDF → simulation + rosbag → diagnostic rosbags → ≤ 3 itérations) ; configurer `SHODH_API_KEYS` (utilisateur) pour les appels memory ; décision fork `mcp-rosbags`.
- **Kimi Code** : enregistrer les 5 serveurs MCP côté client (Claude Code/Cursor lisent `.mcp.json` tel quel).
- **Phase 4** : jobs CI colcon + Gazebo headless (xvfb) + Trivy ; mesures RTF caméra+IMU (rendu GPU) ; réduction du pas physique si besoin.
- **Release** : full-auto ; toute nouvelle section `[Unreleased]` sera coupée automatiquement (v0.2.0 déjà publiée pour les phases 1-3).
- **Vault** : fiche projet à jour ; sessions promues ; connaissance gpt-oss en brouillon (promotion après relecture humaine).

## Journal (session du 2026-09-18 soir → 2026-09-19)

| Heure (ET) | Événement |
|---|---|
| ~19:20 | Corrections audit : FreeCAD 1.1.3 localisé ; repo canonique `spkane/freecad-addon-robust-mcp-server` |
| ~19:25–00:05 | Phase 1 (4 builds itératifs) + Phase 2 (paquets, debout 10 s, squat) + Phase 3 (noyau, garde-fous) — détails en sessions vault |
| ~00:30 | Release v0.2.0 (pre-release vérifiée) |
| ~00:40 | **FreeCAD relancé par l'agent** : `AutoStart=True` posé, bridge actif 9875/9877, `tools/list` **83** |
| ~00:45 | **Blender relancé par l'agent** : addon `blender_mcp` installé/activé/prefs sauvées, socket 9876, `tools/list` 31 + **`get_scene_info` sur la scène vivante** |
| ~00:50 | rosbags vendorisé (`rosbags<0.10`), `tools/list` **15** ; memory 38 (appels : clé requise) → **5/5 serveurs vérifiés** |
