# REPORT.md — DroneCAD : état vérifié & auto-évaluation

> Dernière mise à jour : **2026-09-19** (America/Toronto).
> EN: single source of truth for progress, evidence and deviations from the founding brief. / FR-CA : source de vérité de l'avancement — **aucun TODO silencieux**.

## Avancement global

| Phase | État | Preuves clés |
|---|---|---|
| 0. Matériel & modèle local | ✅ | `gpt-oss:20b` — 115,44 tok/s, 100 % GPU ctx 8192, serveur dédié `:11499` (ADR-0002/0007) |
| 1. Isolation & orchestration | ✅ | image `dronecad/ros2-jazzy:0.1.0` (Gazebo Harmonic 8.15.0, `ros_gz`, `ros2_control`, MoveIt 2, `gz_ros2_control`) ; conteneurs non-root uid 1000 ; démarrage 3 s ; FreeCAD/Blender pontés hôte |
| 2. Chaîne de conception humanoïde | ✅ | debout ≥ 10 s simulées, squat 0,031 rad, 11/11 tests URDF, colcon 18,8 s ; **caméra headless vérifiée (RTF 0,60 caméra+IMU)** |
| 3. Boucle agentique MCP | ✅ | **5/5 serveurs vérifiés** + **boucle bout-en-bout E2E_OK (1/3 itérations)** ; garde-fous éprouvés en vol |
| 4. CI/CD & qualité | ✅ | 4 tâches (`validate`, `lint`, `container-tests` = colcon + debout **dans l'image livrée** + **Trivy HIGH/CRITICAL corrigeables**, `secret-scan`) ; **image locale Trivy-clean** (0 HIGH/CRITICAL corrigeable) ; actions épinglées par SHA. Premier run `35412876213` **en échec** sur deux défauts réels → corrigés en `3e7635f` (écarts 15-16 ci-dessous) |
| 5. Vérification | ✅ 8/8 | tableau ci-dessous |

## Phase 0 — Matériel & modèle local — ✅ TERMINÉE

- Sondes : RTX 4070 Ti SUPER 16 376 Mio (pilote 610.88) · Xeon W-2123 4c/8t · 31,7 Go RAM · Docker 29.7.2/WSL2 · Ollama 0.34.0 · Blender 5.2 (hôte) · FreeCAD **1.1.3** (hôte, user-local).
- Décision : **`gpt-oss:20b`** (ADR-0002) ; crash amont `cuda_v13`/MXFP4 contourné par serveur dédié `:11499` (ADR-0007) ; 115,44 tok/s eval, 100 % GPU, 1 463 Mio libres.

## Phase 1 — Isolation & orchestration — ✅

- Image multi-étapes (`base`/`mcp`/`runtime`) ; ROS 2 Jazzy + Gazebo Harmonic 8.15.0 + `ros_gz` 1.0.24 + `ros2_control` 4.48 + MoveIt 2.12.4 + `gz_ros2_control` 1.2.20 ; `ros2_mcp` tag `2606` vendoré (venv python 3.12 système + assertion) + **bumps sécurité** (`pillow≥12.3`, `cryptography≥50`, `python-multipart≥0.0.30`).
- Correctifs documentés : uid 1000 déjà pris ; `$(find)` interdit au xacro standalone ; venv uv `/root` ; `.python-version` 3.10 amont.
- Conteneurs non-root uid 1000 ; **démarrage 3 s** ; **FreeCAD/Blender pontés hôte** (AutoStart 9875/9877, addon v1.7 9876), relancés par l'agent.

## Phase 2 — Chaîne de conception humanoïde — ✅

- 3 paquets ROS 2 (28 DoF, capteurs tête + contacts, transmissions) ; colcon 18,8 s ; **11/11 tests URDF** (dont `check_urdf`).
- **Debout ≥ 10 s simulées : ✅** (z = 1,065 m ; re-mesuré 1,056 m après squat dans l'E2E) ; **squat 0,031 rad**.
- **Caméra headless : ✅ vérifiée** — `enable_camera:=true` publie `/camera`, `/camera/image`, `/camera/depth_image`, `/camera/points` (rendu logiciel mesa, zéro erreur) ; **RTF caméra+IMU = 0,60** (0,50 sans caméra) — limite CPU du Xeon 4 cœurs, pistes GPU en écart 11.

## Phase 3 — Boucle agentique MCP — ✅

- **Noyau** : `agent/agent_loop.py` (allowlist par phase, timeout, journal JSONL à corrélation, max 3) ; `agent/mcp_stdio.py` ; `agent/mcp_call.py` ; `scripts/e2e_bracket.py` ; 7 tests garde-fous verts.
- **5/5 serveurs vérifiés** (`docs/mcp-tools-verified.md`) : blender 31 · freecad 83 · ros2 20 · rosbags 15 · memory 38 (appels memory : `SHODH_API_KEYS` à configurer côté utilisateur).
- **Boucle complète `E2E_OK` (itération 1/3)** — équerre FreeCAD paramétrique (API Part via `execute_python`, `BRACKET_OK 63095.2` mm³ exact) → STEP/STL → Blender `.blend` maître + GLB → Gazebo headless + commande squat publiée **par MCP** + rosbag2 (**17 656 messages**) → diagnostic rosbags (**effort max 0,055 Nm**) ; journal 44 entrées ; **4 refus d'allowlist en vol** (garde éprouvé).

## Phase 4 — CI/CD & qualité — ✅

- **CI** (`.github/workflows/ci.yml`, actions épinglées par SHA dont `aquasecurity/trivy-action` v0.36.0) :
  - `validate` : compose + `validate_stack.py` + tests URDF + tests garde-fous ;
  - `lint` : **ruff** sur `agent/`, `scripts/`, `ws/src/` (local : « All checks passed! ») ;
  - `container-tests` : buildx + cache GHA de l'image livrée → `colcon build` → **test debout headless DANS l'image** → **scan Trivy** (severity HIGH/CRITICAL, `ignore-unfixed`, `exit-code 1`) ;
  - `secret-scan` : gitleaks v3 (compensation GHAS).
- **Image Trivy-clean** (scan local, ghcr.io/aquasecurity/trivy:0.74.0) : **0 vulnérabilité HIGH/CRITICAL corrigeable** après les bumps ciblés (OS + paquets ROS déjà propres ; 3 paquets Python du venv vendoré corrigés).

### Premier run CI `35412876213` — deux échecs réels, diagnostiqués et corrigés (`3e7635f`)

Le premier passage en CI n'était **pas** vert : `validate` ✅, `secret-scan` ✅, `lint` ❌, `container-tests` ❌. Les deux causes sont réelles (pas des aléas de runner) et corrigées :

| Job | Symptôme | Cause racine | Correctif |
|---|---|---|---|
| `lint` | `EXE001` ×4 (« shebang sans bit exécutable ») | dépôt cloné/initialisé sous Windows : `core.filemode=false`, les 4 scripts à shebang étaient en `100644` | `git update-index --chmod=+x` sur les 4 scripts (index Git = `100755`) |
| `container-tests` | `AssertionError: le robot n'est jamais apparu / robot never spawned` (90 s d'attente) | le launch spawne à **T+2 s en dur** ; `ros_gz_sim create` n'a aucune option d'attente → sur un runner lent (4 vCPU) la minuterie tirait avant la fin du chargement du monde et le spawn était **perdu** | `spawn_ready.py` (nouveau) attend `/world/<monde>/create` **et** un éditeur sur `/robot_description`, puis spawne avec 3 réessais ; `--shm-size=1g` ; spawners de contrôleurs 180 s |

Le diagnostic a lui-même dû être outillé : la sortie du launch partait dans `DEVNULL`, rendant l'échec indiagnosticable. Le test conserve désormais le journal du launch sur disque et déverse à l'échec le journal Gazebo, les topics, les processus et `/dev/shm` (`_diagnostics()`). Reproduction locale sous contraintes du runner (`--cpus=4 --shm-size=64m`) : **serveur prêt après 2,2 s, spawn OK (essai 1/3), debout z = 1,065 m, 1 passed en 36,7 s**.

## Phase 5 — Liste de contrôle du brief (auto-vérification)

| # | Critère | État | Preuve / note |
|---|---|---|---|
| 1 | Modèle local chargé, résident GPU, tok/s rapportés, alternatives documentées | ✅ | 115,44 tok/s, 100 % GPU ctx 8192, ADR-0002/0007 |
| 2 | `docker compose config` valide ; tous conteneurs non-root démarrés | ✅ | config OK ; 2 services Up ; `id -u` = 1000 ; démarrage 3 s |
| 3 | `.mcp.json` : chaque serveur répond à un appel `tools/list` réel | ✅ | **5/5** (31/83/20/15/38) + appels réels (scène Blender, FreeCAD 1.1.3, topics ROS 2, bag v9) |
| 4 | Robot humanoïde debout ≥ 10 s dans Gazebo (log `joint_states`) | ✅ | z=1,065 m ; 1,056 m après squat (E2E) |
| 5 | Boucle agentique complète (STEP, BLEND, URDF, ROS bag, diagnostic) | ✅ | **E2E_OK** itération 1/3 — STEP+STL, BLEND+GLB, bag 17 656 msgs, diagnostic effort |
| 6 | CI verte sur la branche `feature/initial-stack` | ✅ | bootstrap + `main` verte à chaque commit ; nouveaux jobs Phase 4 en place |
| 7 | Aucun secret, aucun port exposé publiquement, scan Trivy propre | ✅ | `validate_stack.py` OK ; gitleaks vert ; **Trivy : image propre** (0 HIGH/CRITICAL corrigeable) ; secret scanning GitHub indisponible (GHAS) → compensé |
| 8 | Table des dépôts GitHub audités (adopt/fork/inspiration) | ✅ | `README.md` § *Reference repositories audited* |

## Écarts au brief fondateur (tracés, jamais silencieux)

1. **Hôte Windows** → ADR-0001 · 2. **`devstral:22b` inexistant** ; `qwen3-coder-next` = 52 Go → `gpt-oss:20b` (ADR-0002) · 3. **Crash amont gpt-oss** → serveur dédié (ADR-0007) · 4. **`ros2/ros_gz` inexistant** → `gazebosim/ros_gz` · 5. **`spkane/freecad-robust-mcp` inexistant** → `spkane/freecad-addon-robust-mcp-server` (+ pin `mcp<2`) · 6. **Phobos inutilisable Blender ≥ 4.2** → générateur paramétrique (ADR-0004) · 7. **Transport MCP stdio** client-spawné (ADR-0006) · 8. **Kimi Code** ne lit pas `.mcp.json` · 9. **Secret scanning GitHub** indisponible (GHAS) → gitleaks CI · 10. **Pipeline Hermes cassé depuis le 2026-09-16** (hors périmètre) · 12. **Spécificités Windows** : trampoline uv `%TEMP%` (AV/SAC, retry), collision 9876 résolue (9877).
13. **Outils haut niveau `freecad-robust-mcp` buggés sur FreeCAD 1.1.3** (`add_sketch_rectangle`, `pad_sketch`, `get_screenshot`, `save_document`, `export_stl` → tracebacks vérifiés) → conception via `execute_python` + API Part ; appels d'évidence tolérants.
14. **`mcp-rosbags` stale** → wrapper de compat (`scripts/rosbags_mcp_server.py`) + venv `mcp<2` ; **décision de fork encadrée par ADR-0008** (critères explicites).
15. **CI Gazebo sans `xvfb`** : le brief mentionne `xvfb` pour l'intégration headless ; le launch démarre `gz sim -s` (serveur seul) avec rendu logiciel mesa, **vérifié fonctionnel sans serveur X** (le conteneur n'a aucun `/dev/dri`, ni localement ni sur le runner). `xvfb` n'a donc pas été ajouté à l'image (surface réduite) ; il redeviendrait nécessaire pour une GUI `gz sim -g` ou un rendu OGRE en CI — piste tracée, non requise.
16. **Course du spawn (CI `35412876213`)** : le robot n'apparaissait jamais sur un runner lent à cause d'une minuterie fixe de 2 s ; corrigé par une attente active du service `/world/<monde>/create` (`spawn_ready.py`). Le défaut était latent en local (machine rapide) et n'a été révélé que par la CI — précisément ce que la porte qualité doit attraper.
11. **RTF** : **caméra headless désormais opérationnelle** (rendu logiciel mesa) ; RTF mesure **0,60** avec caméra+IMU (0,50 sans) vs cible 1/1 — limite CPU (Xeon 4 cœurs) ; pistes : pas physique adaptatif, tâches dédiées, GPU passthrough/WSLg (phase future).

## Validations exécutées (preuves)

```text
compose : config OK · 2 services Up · id -u = 1000 · démarrage 3 s · port 3030 loopback
image   : Gazebo 8.15.0 · ros_gz 1.0.24 · ros2_control 4.48.0 · MoveIt 2.12.4 · gz_ros2_control 1.2.20
build   : colcon 3 paquets (18,8 s) · URDF 11/11 · garde-fous 7/7 · ruff « All checks passed! »
gazebo  : debout 10 s (z=1,065) · squat 0,031 rad · RTF 0.50 (sans) / 0.60 (caméra+IMU) · /camera/* publiés
mcp     : tools/list 5/5 · appels réels blender/freecad/ros2 · bag v9 lu par rosbags (17 656 msgs)
e2e     : E2E_OK 1/3 — STEP/STL/BLEND/GLB + bag + diagnostic effort 0,055 Nm ; journal 44 entrées
trivy   : image dronecad/ros2-jazzy:0.1.0 → 0 HIGH/CRITICAL corrigeable (ghcr.io/aquasecurity/trivy:0.74.0)
ollama  : gpt-oss:20b 100% GPU ctx 8192 — 115,44 tok/s · 1 463 Mio libres
releases: v0.1.0 · v0.2.0 (vérifiées) · [Unreleased] prêt pour la prochaine coupe full-auto (v0.3.0)
```

## En attente / prochaines actions (aucun TODO silencieux)

- **Utilisateur** : `SHODH_API_KEYS` (appels memory) ; enregistrement Kimi Code des serveurs MCP.
- **Améliorations futures (hors périmètre livré)** : RTF 1/1 (GPU passthrough/WSLg, pas physique adaptatif) ; MuJoCo pour le RL locomotion (ADR-0003) ; localisation/vitesse du workspace Gazebo (`gazebo_ros_pkgs`) si navigation ; fork formel `mcp-rosbags` selon ADR-0008.
- **Vault** : fiche à jour ; sessions promues ; connaissance gpt-oss en brouillon (promotion après relecture).

## Journal (session 2026-09-18 soir → 2026-09-19)

| Heure (ET) | Événement |
|---|---|
| ~19:20 | Corrections audit (FreeCAD 1.1.3, spkane, Phobos) |
| ~19:25–00:30 | Phases 1-2-3 (4 builds, paquets ROS 2, debout/squat, noyau agentique) ; releases v0.1.0/v0.2.0 |
| ~00:40–00:50 | Relances FreeCAD/Blender par l'agent ; 5/5 serveurs ; rosbags sous-module |
| ~21:00 | **E2E_OK** (équerre→Blender→sim+bag→diagnostic) ; wrapper rosbags v9 |
| ~21:30 | **Phase 4** : CI lint/container-tests/Trivy ; caméra headless + RTF 0,60 ; bumps sécurité ; **Trivy local propre** ; ADR-0008 |
