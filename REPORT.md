# REPORT.md — DroneCAD : état vérifié & auto-évaluation

> Dernière mise à jour : **2026-09-19** (America/Toronto).
> EN: single source of truth for progress, evidence and deviations from the founding brief. / FR-CA : source de vérité de l'avancement — **aucun TODO silencieux**.

## Avancement global

| Phase | État | Preuves clés |
|---|---|---|
| 0. Matériel & modèle local | ✅ | `gpt-oss:20b` — 115,44 tok/s, 100 % GPU ctx 8192, serveur dédié `:11499` (ADR-0002/0007) |
| 1. Isolation & orchestration | ✅ | image `dronecad/ros2-jazzy:0.1.0` (Gazebo Harmonic 8.15.0, `ros_gz`, `ros2_control`, MoveIt 2, `gz_ros2_control` ; `ros2_mcp` vendoré) ; conteneurs non-root uid 1000 ; démarrage 3 s ; FreeCAD/Blender hôtes pontés (AutoStart) |
| 2. Chaîne de conception humanoïde | ✅ | debout ≥ 10 s simulées, squat 0,031 rad, 11/11 tests URDF, colcon 18,8 s, RTF 0,50 (sans caméra) |
| 3. Boucle agentique MCP | ✅ | **5/5 serveurs vérifiés** + **boucle bout-en-bout exécutée (E2E_OK, 1/3 itérations)** — voir § Phase 3 |
| 4. CI/CD & qualité | 🟡 minimal | `validate` (compose + stack + URDF + garde-fous) et `secret-scan` verts ; colcon/Gazebo-headless/Trivy en CI = à ajouter |
| 5. Vérification | ✅ 7 / 🟡 1 | tableau ci-dessous (seul Trivy reste partiel) |

## Phase 0 — Matériel & modèle local — ✅ TERMINÉE

- Sondes : RTX 4070 Ti SUPER 16 376 Mio (pilote 610.88) · Xeon W-2123 4c/8t · 31,7 Go RAM · Docker 29.7.2/WSL2 · Ollama 0.34.0 · Blender 5.2 (hôte) · FreeCAD **1.1.3** (hôte, user-local).
- Décision : **`gpt-oss:20b`** (ADR-0002) ; crash amont `cuda_v13`/MXFP4 contourné par serveur dédié `:11499` (ADR-0007) ; 115,44 tok/s eval, 222,96 prefill, 100 % GPU, 1 463 Mio libres.

## Phase 1 — Isolation & orchestration — ✅

- Image multi-étapes (`base`/`mcp`/`runtime`) ; ROS 2 Jazzy + Gazebo Harmonic 8.15.0 + `ros_gz` 1.0.24 + `ros2_control` 4.48 + MoveIt 2.12.4 + `gz_ros2_control` 1.2.20 ; `ros2_mcp` tag `2606` vendoré (venv python 3.12 système + assertion).
- Correctifs documentés : uid 1000 déjà pris (`ros:jazzy`) ; `$(find)` interdit au xacro standalone ; venv uv `/root` inaccessible ; `.python-version` 3.10 amont.
- Conteneurs non-root uid 1000, `shodh` healthy, port 3030 loopback ; **démarrage 3 s** (cible < 90 s ✅).
- **FreeCAD/Blender pontés côté hôte** : `robust-mcp` v0.6.2 (`AutoStart=True`, XML-RPC 9875, socket déplacé 9877) ; addon `blender_mcp` v1.7 activé (socket 9876) — **relancés par l'agent**.

## Phase 2 — Chaîne de conception humanoïde — ✅

- 3 paquets ROS 2 (28 DoF, capteurs tête + contacts, transmissions) ; colcon 18,8 s ; **11/11 tests URDF** (dont `check_urdf`).
- **Debout ≥ 10 s simulées : ✅** (z = 1,065 m, roll/pitch ≈ 0) ; **squat 0,031 rad** (seuil 0,25) ; RTF 0,50 sans caméra (écart 11).

## Phase 3 — Boucle agentique MCP — ✅ **BOUCLE BOUT-EN-BOUT EXÉCUTÉE**

- **Noyau** : `agent/agent_loop.py` (allowlist par phase, timeout par appel, journal JSONL à corrélation, max 3 itérations) ; `agent/mcp_stdio.py` (client stdio JSON-RPC 2.0, zéro dépendance) ; `agent/mcp_call.py` ; `scripts/e2e_bracket.py` ; 7 tests garde-fous verts.
- **5/5 serveurs vérifiés** (`tools/list` + appels réels — `docs/mcp-tools-verified.md`) : blender 31 · freecad 83 · ros2 20 · rosbags 15 · memory 38 (appels memory : `SHODH_API_KEYS` requis — configuration utilisateur).
- **Boucle complète `E2E_OK` (itération 1/3)** — `scripts/e2e_bracket.py`, journal `artifacts/e2e_journal.jsonl` (44 entrées) :

```text
design   : execute_python → "BRACKET_OK 63095.2" — équerre 80×100×8 mm, trou Ø12 (API Part, paramétrique)
           → motor_bracket.step (8,4 Ko) + motor_bracket.stl (26 Ko)     [FreeCAD 1.1.3, GUI visible]
model    : Blender import STL + enveloppe filaire → motor_bracket_master.blend (106 Ko) + dronecad_enclosure.glb (24 Ko)
simulate : Gazebo headless + rosbag2 → e2e_bag_0.mcap (3,8 Mo) ; commande squat publiée PAR MCP
           (ros2_topic_publish, 4,3 s) ; pose finale z = 1,056 m → PAS DE CHUTE
analyze  : rosbags MCP → bag_info (17 656 messages : /clock 13 633, /imu 2 710, /joint_states …)
           + /joint_states désérialisés (169 936 car.) → effort max 0,055 Nm << 150 Nm
critères : fichiers ✅ · bag ✅ · pas de chute ✅ · couple ✅ → succès itération 1
```

- **Garde-fous éprouvés en vol** : 4 refus d'allowlist journalisés (dont `export_stl` et `list_objects` avant ajout) — le garde bloque réellement, jamais de contournement ;
- **Itération paramétrique** implémentée (ajustement du genou ×0,8 + re-run, plafond 3) — non déclenchée car critères verts du premier coup ;
- **Décisions techniques documentées** (écarts 13-14) : outils haut niveau `freecad-robust-mcp` buggés sur 1.1.3 → `execute_python` + API Part ; serveur `mcp-rosbags` stale → **wrapper de compat** (`scripts/rosbags_mcp_server.py`, rosbags moderne + shims) + venv dédié (`mcp<2`, `scripts/setup_rosbags_vendor.ps1`).
- **Reste** : enregistrement Kimi Code des serveurs (ne lit pas `.mcp.json`) ; `SHODH_API_KEYS` pour les appels memory ; décision fork formelle `mcp-rosbags` (le wrapper tient lieu d'intérim).

## Phase 5 — Liste de contrôle du brief (auto-vérification)

| # | Critère | État | Preuve / note |
|---|---|---|---|
| 1 | Modèle local chargé, résident GPU, tok/s rapportés, alternatives documentées | ✅ | 115,44 tok/s, 100 % GPU ctx 8192, ADR-0002/0007 |
| 2 | `docker compose config` valide ; tous conteneurs non-root démarrés | ✅ | config OK ; 2 services Up ; `id -u` = 1000 ; démarrage 3 s |
| 3 | `.mcp.json` : chaque serveur répond à un appel `tools/list` réel | ✅ | **5/5** (31/83/20/15/38) + appels d'outils réels (scène Blender, FreeCAD 1.1.3, topics ROS 2, bag v9) |
| 4 | Robot humanoïde debout ≥ 10 s dans Gazebo (log `joint_states`) | ✅ | z=1,065 m ; de nouveau 1,056 m après squat dans l'E2E |
| 5 | Boucle agentique complète (STEP, BLEND, URDF, ROS bag, diagnostic) | ✅ | **E2E_OK** : STEP+STL, BLEND+GLB, bag 17 656 msgs, diagnostic effort/trajectoire ; URDF régénéré par la chaîne ADR-0004 |
| 6 | CI verte sur la branche `feature/initial-stack` | ✅ | bootstrap + `main` verte à chaque commit |
| 7 | Aucun secret, aucun port exposé publiquement, scan Trivy propre | 🟡 | `validate_stack.py` OK ; gitleaks vert ; secret scanning GitHub indisponible (GHAS) → compensé ; Trivy = Phase 4 |
| 8 | Table des dépôts GitHub audités (adopt/fork/inspiration) | ✅ | `README.md` § *Reference repositories audited* |

## Écarts au brief fondateur (tracés, jamais silencieux)

1. **Hôte Windows** → ADR-0001 · 2. **`devstral:22b` inexistant** ; `qwen3-coder-next` = 52 Go → `gpt-oss:20b` (ADR-0002) · 3. **Crash amont gpt-oss** → serveur dédié (ADR-0007) · 4. **`ros2/ros_gz` inexistant** → `gazebosim/ros_gz` · 5. **`spkane/freecad-robust-mcp` inexistant** → `spkane/freecad-addon-robust-mcp-server` (+ pin `mcp<2`) · 6. **Phobos inutilisable Blender ≥ 4.2** → générateur paramétrique (ADR-0004) · 7. **Transport MCP stdio** client-spawné (ADR-0006) · 8. **Kimi Code** ne lit pas `.mcp.json` · 9. **Secret scanning GitHub** indisponible (GHAS) → gitleaks CI · 10. **Pipeline Hermes cassé depuis le 2026-09-16** (hors périmètre) · 11. **Caméra/RTF** : tests headless caméra off, RTF 0,50 · 12. **Spécificités Windows** : trampoline uv `%TEMP%` (AV/SAC, retry), collision 9876 résolue (9877).
13. **Outils haut niveau `freecad-robust-mcp` buggés sur FreeCAD 1.1.3** (vérifié : tracebacks dans `add_sketch_rectangle`, `pad_sketch`, `get_screenshot`, `save_document`, `export_stl`) → conception via `execute_python` + API Part (paramétrique, GUI visible) ; appels d'évidence tolérants ; signalé à l'amont le cas échéant.
14. **`mcp-rosbags` stale** : API rosbags pré-0.10 (bags v9 illisibles) + `mcp` 2.x incompatible (`Server.list_tools()` retiré) → wrapper `scripts/rosbags_mcp_server.py` (rosbags moderne + shims) + venv dédié pinné `mcp<2` ; décision de fork formelle à acter si le vendor reste figé.

## Validations exécutées (preuves)

```text
compose : config OK · 2 services Up · id -u = 1000 · démarrage 3 s · port 3030 loopback
image   : Gazebo 8.15.0 · ros_gz 1.0.24 · ros2_control 4.48.0 · MoveIt 2.12.4 · gz_ros2_control 1.2.20
build   : colcon 3 paquets (18,8 s) · URDF 11/11 · garde-fous 7/7 · CI verte (validate + secret-scan)
gazebo  : debout 10 s (z=1,065) · squat 0,031 rad · RTF 0.50 (sans caméra)
mcp     : tools/list 5/5 · appels réels blender/freecad/ros2 · bag v9 lu par rosbags (17 656 msgs)
e2e     : E2E_OK itération 1/3 — STEP/STL/BLEND/GLB + bag + diagnostic effort 0,055 Nm ; journal 44 entrées
ollama  : gpt-oss:20b 100% GPU ctx 8192 — 115,44 tok/s · 1 463 Mio libres
releases: v0.1.0 · v0.2.0 (vérifiées gh release view) · [Unreleased] prêt pour la prochaine coupe full-auto
```

## En attente / prochaines actions (aucun TODO silencieux)

- **Utilisateur** : `SHODH_API_KEYS` (appels memory) ; enregistrement Kimi Code des serveurs MCP ; décision mode de release inchangée (full-auto).
- **Phase 4** : jobs CI colcon + Gazebo headless (xvfb) + Trivy ; mesures RTF caméra+IMU (rendu GPU passthrough).
- **Fork formel** `mcp-rosbags` si le wrapper devient trop lourd (upstream figé depuis 2025-09).
- **Vault** : fiche à jour ; sessions promues ; connaissance gpt-oss en brouillon (promotion après relecture).

## Journal (session 2026-09-18 soir → 2026-09-19)

| Heure (ET) | Événement |
|---|---|
| ~19:20 | Corrections audit : FreeCAD 1.1.3 ; repo canonique spkane ; Phobos |
| ~19:25–00:05 | Phases 1-2 (4 builds itératifs, paquets ROS 2, debout 10 s, squat) + Phase 3 noyau |
| ~00:30 | Release v0.2.0 (pre-release vérifiée) |
| ~00:40–00:50 | Relances FreeCAD (AutoStart 9875/9877) et Blender (addon v1.7, 9876) par l'agent ; 5/5 serveurs ; rosbags sous-module |
| ~21:00 | E2E : équerre paramétrique (execute_python), Blender, sim+bag (17 656 msgs), diagnostic — **E2E_OK 1/3** ; wrapper rosbags v9 ; garde-fous éprouvés en vol |
