# Changelog — DroneCAD

Toutes les modifications notables de ce projet sont documentées ici.
Format : [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/) · Versioning : [SemVer](https://semver.org/lang/fr/) · Horodatage ISO 8601 (fuseau local).
Les releases sont *delivery-gated* et **full-auto** : gérées par `.harness/scripts/release-check.py` (déclaré le 2026-09-18, mode `full-auto`).

## [Unreleased]

### Added

- **Phase 4 (CI)** — jobs `lint` (ruff sur `agent/`, `scripts/`, `ws/src/`), `container-tests` (buildx + cache GHA → colcon + tests URDF + **test debout headless dans l'image livrée** + **scan Trivy** HIGH/CRITICAL corrigeables) ; concurrence annulée par réf ; actions épinglées par SHA (dont `aquasecurity/trivy-action` v0.36.0).
- **Caméra headless vérifiée** : `enable_camera:=true` publie `/camera`, `/camera/image`, `/camera/depth_image`, `/camera/points` (rendu logiciel mesa, zéro erreur) ; **RTF caméra+IMU mesuré à 0,60** (vs 0,50 sans caméra — limite CPU documentée, écart 11).
- ADR-0008 : décision `mcp-rosbags` (wrapper de compatibilité, critères de fork explicites).
- **Boucle agentique bout-en-bout** (`scripts/e2e_bracket.py`) exécutée et vérifiée : FreeCAD (équerre paramétrique via `execute_python` → STEP/STL) → Blender (import + enveloppe → `.blend` maître + GLB) → Gazebo headless + commande squat publiée par `ros2_topic_publish` (MCP) + rosbag2 (17 656 messages) → diagnostic rosbags (effort max 0,055 Nm) — **4/4 critères, 1 itération sur 3** ; journal JSONL à corrélation (`artifacts/e2e_journal.jsonl`).
- `scripts/rosbags_mcp_server.py` — wrapper de compatibilité du serveur `mcp-rosbags` vendoré (rosbags moderne pour les bags Jazzy v9 + shims `deserialize_cdr`/`serialize_cdr`) ; `scripts/setup_rosbags_vendor.ps1` (venv dédié, pin `mcp<2`).
- `agent/mcp_call.py` — appel direct d'un outil MCP (diagnostic/opérations).

### Fixed

- **CI Phase 4 — cinq runs en échec (`35412876213` → `35416093199`), quatre défauts réels corrigés** : (1) job `lint` → `EXE001` (shebang sans bit exécutable — artefact d'un dépôt cloné sous Windows, `core.filemode=false`) → bit exécutable posé dans l'index Git sur les 4 scripts, puis `I001` (import `PythonExpression` réparti multiligne) ; (2) le spawn du robot reposait sur une minuterie fixe de 2 s et était **perdu** sur un runner lent → nouveau `spawn_ready.py` qui attend `/world/<monde>/create` **et** un éditeur sur `/robot_description` avant de spawner (3 réessais) ; (3) le monde du test chargeait `gz-sim-sensors-system` (moteur OGRE2), inutile et dépendant d'un contexte graphique → nouveau monde **`flat_ground_headless.sdf`** ; (4) **cause racine du robot absent** : le job tournait avec `--user "$(id -u):$(id -g)"`, soit l'uid 1001 du runner, **absent de `/etc/passwd`** de l'image — gz-transport ne se découvre alors plus du tout et le serveur, pourtant pleinement initialisé, n'annonce aucun topic (reproduit sur la station : uid 1000 → topics listés, uid 1001 → muet) ; smoke et test debout tournent désormais en **uid 1000** (`ubuntu` de l'image), espace de travail en lecture seule, cache pytest redirigé. Au passage : `--shm-size=1g`, timeouts élargis (serveur 180 s, contrôleurs 180 s, test 600 s), **journal du launch conservé sur disque + diagnostic automatique à l'échec** (journaux Gazebo, topics, processus, `/dev/shm`), et une étape de fumée « le serveur annonce `/clock` » qui sépare « le simulateur démarre » de « le robot tient debout ».
- **Sécurité image** : bumps ciblés dans le venv vendoré (`anyio>=4.14.2`, `pillow>=12.3.0`, `cryptography>=50.0.0`, `python-multipart>=0.0.30`) — le scan CI a détecté **1 CRITICAL corrigeable** (`anyio` 4.9.0, CVE-2026-63374 — encodage IDNA-2003 du nom d'hôte dans `TLSStream`), en plus des constats traités précédemment ; serveur MCP ros2 revérifié après le bump (réponse JSON-RPC). Vérifié après coup dans l'image reconstruite : `anyio 4.15.1`, `mcp 1.28.1`.
- Lint : 20+ constats ruff corrigés (agent, scripts, tests ROS 2) ; `preexec_fn=os.setsid` → `start_new_session=True` dans le test debout.
- Outils haut niveau `freecad-robust-mcp` buggés sur FreeCAD 1.1.3 (`add_sketch_rectangle`, `pad_sketch`, `get_screenshot`, `save_document`, `export_stl` → tracebacks internes vérifiés) : la conception passe par `execute_python` + API Part, les appels d'évidence sont tolérants (décision rapportée dans `REPORT.md`).
- Serveur `mcp-rosbags` inutilisable en l'état (dépôt stale : API rosbags pré-0.10, incompatible bags v9 ; `mcp` 2.x sans `Server.list_tools()`) → wrapper + venv dédié.
- `.mcp.json` : expansion `${DRONECAD_HOME}` ajoutée au client interne ; entrée rosbags recâblée sur le venv vendoré.

## [v0.2.0] - 2026-09-18

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
