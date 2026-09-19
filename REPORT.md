# REPORT.md — DroneCAD : état vérifié & auto-évaluation

> Dernière mise à jour : **2026-09-19** (America/Toronto) — CI verte (run `35418441478`).
> EN: single source of truth for progress, evidence and deviations from the founding brief. / FR-CA : source de vérité de l'avancement — **aucun TODO silencieux**.

## Avancement global

| Phase | État | Preuves clés |
|---|---|---|
| 0. Matériel & modèle local | ✅ | `gpt-oss:20b` — 115,44 tok/s, 100 % GPU ctx 8192, serveur dédié `:11499` (ADR-0002/0007) |
| 1. Isolation & orchestration | ✅ | image `dronecad/ros2-jazzy:0.1.0` (Gazebo Harmonic 8.15.0, `ros_gz`, `ros2_control`, MoveIt 2, `gz_ros2_control`) ; conteneurs non-root uid 1000 ; démarrage 3 s ; FreeCAD/Blender pontés hôte |
| 2. Chaîne de conception humanoïde | ✅ | debout ≥ 10 s simulées, squat 0,031 rad, 11/11 tests URDF, colcon 18,8 s ; **caméra headless vérifiée (RTF 0,60 caméra+IMU)** |
| 3. Boucle agentique MCP | ✅ | **5/5 serveurs vérifiés** + **boucle bout-en-bout E2E_OK (1/3 itérations)** ; garde-fous éprouvés en vol |
| 4. CI/CD & qualité | ✅ | **CI verte — run `35418441478`** (les 4 tâches : `validate`, `lint`, `container-tests` = colcon + **fumée Gazebo** + debout **dans l'image livrée** + **Trivy HIGH/CRITICAL corrigeables**, `secret-scan`) ; actions épinglées par SHA. Cinq runs rouges avant le vert : quatre défauts réels + une CVE CRITICAL corrigée (voir § *Porte qualité CI*) |
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

### Porte qualité CI — cinq runs, quatre défauts réels corrigés (`3e7635f` → `0503a21`)

La CI n'a **pas** été verte du premier coup. Chaque échec a été instrumenté, diagnostiqué, corrigé puis re-vérifié — jamais contourné ni maquillé.

| # | Run(s) | Symptôme | Cause racine | Correctif |
|---|---|---|---|---|
| 1 | `35412876213` | `lint` : `EXE001` ×4 | dépôt initialisé sous Windows (`core.filemode=false`) → shebangs en `100644` | `git update-index --chmod=+x` sur les 4 scripts |
| 2 | `35412876213` | « le robot n'est jamais apparu » (90 s) | spawn sur **minuterie fixe de 2 s** ; `ros_gz_sim create` n'attend rien → spawn perdu sur un runner lent | `spawn_ready.py` (attend `/world/<monde>/create` **et** l'éditeur du topic), `--shm-size=1g`, contrôleurs 180 s |
| 3 | `35413419667` | même échec, 180 s | sortie du launch dans `DEVNULL` → **échec indiagnosticable** | journal du launch sur disque + `_diagnostics()` (journaux Gazebo, topics, processus, `/dev/shm`) |
| 4 | `35413853829` | `gz topic -l` **et** `ros2 node list` vides | le monde chargeait `gz-sim-sensors-system` (moteur OGRE2) | monde **`flat_ground_headless.sdf`** + étape de fumée dédiée |
| 5 | `35414244557` → `35416093199` | serveur pleinement initialisé (`World [flat_ground_headless] initialized`) mais **aucun** topic à 20/45/90/150 s, à ~26 % CPU | `--user "$(id -u):$(id -g)"` = **uid 1001 du runner, absent de `/etc/passwd`** → gz-transport ne se découvre plus | uid **1000** (`ubuntu` de l'image) pour les étapes Gazebo, espace de travail en lecture seule, cache pytest en `/tmp` |

Le test décisif (reproduit sur la station, avec l'image livrée) :

```text
docker run --user 1000:1000 … → gz topic -l : /clock  /gazebo/resource_paths  /stats  …
docker run --user 1001:1001 … → gz topic -l : (vide)
```

Pistes explorées puis **écartées par la mesure** (elles n'étaient pas la cause) : `--network host`, `GZ_IP=127.0.0.1`, `ROS_LOCALHOST_ONLY`/`ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST`, profil Fast DDS sans multicast (écrit, validé contre `fastRTPS_profiles.xsd`, puis supprimé faute d'utilité), `shm-size` porté à 1 Gio, attentes allongées. Les flags multicast des interfaces sont d'ailleurs **identiques** en local et en CI (`lo: 0x9`, `eth0: 0x1003`).

Ce que la CI protège désormais (job `container-tests`) : build de l'image livrée → `colcon build` + tests URDF → **fumée du serveur Gazebo** (« `/clock` annoncé ») → **test debout dans l'image** (10 s simulées, base z = 1,065 m) → **Trivy** HIGH/CRITICAL corrigeables. Vérification locale de la configuration exacte du job (uid 1000, `ws` en lecture seule) : **1 passed en 41,9 s**.

**Dernier obstacle, lui aussi réel : le disque du runner.** Trivy n'a pas signalé de vulnérabilité mais a échoué deux fois, d'abord par manque d'espace (`failed to copy the image: … no space left on device` — l'image de 6,3 Go est exportée décompressée, ~20 Go, pour 8,6 Go libres), puis une fois le scan passé, il a correctement **bloqué le merge** sur une faille : `anyio 4.9.0` — **CVE-2026-63374 (CRITICAL)**, corrigée en 4.14.2. Traitée comme les quatre précédentes : bump ciblé du venv vendoré (`anyio>=4.14.2` → 4.15.1), image reconstruite, serveur MCP ros2 revérifié, versions contrôlées dans l'image.

### ✅ Vert — run `35418441478` (commit `9e7bc84`)

| Job | Étapes | Résultat |
|---|---|---|
| `validate` | compose, `validate_stack.py`, URDF, garde-fous | ✅ |
| `lint` | ruff (`agent/`, `scripts/`, `ws/src/`) | ✅ |
| `container-tests` | image → colcon + 11 tests URDF → **fumée Gazebo** → **debout dans l'image** → **Trivy** | ✅ |
| `secret-scan` | gitleaks | ✅ |

Le test debout tourne donc désormais **en CI, dans l'image livrée**, et la porte qualité a démontré sa valeur : elle a attrapé quatre défauts réels et une CVE CRITICAL qu'aucune vérification locale ne pouvait voir.

## Phase 5 — Liste de contrôle du brief (auto-vérification)

| # | Critère | État | Preuve / note |
|---|---|---|---|
| 1 | Modèle local chargé, résident GPU, tok/s rapportés, alternatives documentées | ✅ | 115,44 tok/s, 100 % GPU ctx 8192, ADR-0002/0007 |
| 2 | `docker compose config` valide ; tous conteneurs non-root démarrés | ✅ | config OK ; 2 services Up ; `id -u` = 1000 ; démarrage 3 s |
| 3 | `.mcp.json` : chaque serveur répond à un appel `tools/list` réel | ✅ | **5/5** (31/83/20/15/38) + appels réels : scène Blender, FreeCAD 1.1.3, topics ROS 2, sac v9 (11 526 msgs), **mémoire locale** (`remember` → `recall` 95 %) |
| 4 | Robot humanoïde debout ≥ 10 s dans Gazebo (log `joint_states`) | ✅ | z=1,065 m ; 1,056 m après squat (E2E) |
| 5 | Boucle agentique complète (STEP, BLEND, URDF, ROS bag, diagnostic) | ✅ | **E2E_OK** itération 1/3 — STEP+STL, BLEND+GLB, bag 17 656 msgs, diagnostic effort |
| 6 | CI verte sur la branche `feature/initial-stack` | ✅ | **run `35418441478` : 4/4 jobs verts** ; `feature/initial-stack` alignée sur ce commit (fast-forward) ; cinq runs rouges d'abord, chaque cause corrigée puis re-vérifiée |
| 7 | Aucun secret, aucun port exposé publiquement, scan Trivy propre | ✅ | `validate_stack.py` OK ; gitleaks vert ; **Trivy : image propre** (0 HIGH/CRITICAL corrigeable) ; secret scanning GitHub indisponible (GHAS) → compensé |
| 8 | Table des dépôts GitHub audités (adopt/fork/inspiration) | ✅ | `README.md` § *Reference repositories audited* |

## Écarts au brief fondateur (tracés, jamais silencieux)

1. **Hôte Windows** → ADR-0001 · 2. **`devstral:22b` inexistant** ; `qwen3-coder-next` = 52 Go → `gpt-oss:20b` (ADR-0002) · 3. **Crash amont gpt-oss** → serveur dédié (ADR-0007) · 4. **`ros2/ros_gz` inexistant** → `gazebosim/ros_gz` · 5. **`spkane/freecad-robust-mcp` inexistant** → `spkane/freecad-addon-robust-mcp-server` (+ pin `mcp<2`) · 6. **Phobos inutilisable Blender ≥ 4.2** → générateur paramétrique (ADR-0004) · 7. **Transport MCP stdio** client-spawné (ADR-0006) · 8. **Kimi Code** ne lit pas `.mcp.json` · 9. **Secret scanning GitHub** indisponible (GHAS) → gitleaks CI · 10. **Pipeline Hermes cassé depuis le 2026-09-16** (hors périmètre) · 12. **Spécificités Windows** : trampoline uv `%TEMP%` (AV/SAC, retry), collision 9876 résolue (9877).
13. **Outils haut niveau `freecad-robust-mcp` buggés sur FreeCAD 1.1.3** (`add_sketch_rectangle`, `pad_sketch`, `get_screenshot`, `save_document`, `export_stl` → tracebacks vérifiés) → conception via `execute_python` + API Part ; appels d'évidence tolérants.
14. **`mcp-rosbags` stale** → wrapper de compat (`scripts/rosbags_mcp_server.py`) + venv `mcp<2` ; **décision de fork encadrée par ADR-0008** (critères explicites).
15. **CI Gazebo sans `xvfb`** : le brief mentionne `xvfb` pour l'intégration headless ; le launch démarre `gz sim -s` (serveur seul) avec rendu logiciel mesa, **vérifié fonctionnel sans serveur X** (le conteneur n'a aucun `/dev/dri`, ni localement ni sur le runner). `xvfb` n'a donc pas été ajouté à l'image (surface réduite) ; il redeviendrait nécessaire pour une GUI `gz sim -g` ou un rendu OGRE en CI — piste tracée, non requise.
16. **Course du spawn (CI `35412876213`)** : le robot n'apparaissait jamais sur un runner lent à cause d'une minuterie fixe de 2 s ; corrigé par une attente active du service `/world/<monde>/create` (`spawn_ready.py`). Le défaut était latent en local (machine rapide) et n'a été révélé que par la CI — précisément ce que la porte qualité doit attraper.
17. **Contrainte d'environnement CI — uid sans entrée `/etc/passwd`** : avec `--user 1001:1001` (l'uid du runner, absent de `/etc/passwd` de l'image), **gz-transport ne se découvre plus du tout** : le serveur Gazebo démarre, charge le monde jusqu'à « World [...] initialized », tourne à ~26 % CPU, et n'annonce aucun topic — d'où cinq runs en échec. Le job exécute donc les étapes Gazebo en **uid 1000** (`ubuntu` de l'image, présent dans `/etc/passwd`), espace de travail monté en lecture seule ; l'étape `colcon` garde l'uid du runner car elle écrit dans l'arborescence. Reproduit et corrigé sur la station (uid 1000 → topics listés ; uid 1001 → muet), puis vérifié avec la configuration exacte du job.
11. **RTF** : **caméra headless désormais opérationnelle** (rendu logiciel mesa) ; RTF mesure **0,60** avec caméra+IMU (0,50 sans) vs cible 1/1 — limite CPU (Xeon 4 cœurs) ; pistes : pas physique adaptatif, tâches dédiées, GPU passthrough/WSLg (phase future).

## Validations exécutées (preuves)

```text
compose : config OK · 2 services Up · id -u = 1000 · démarrage 3 s · port 3030 loopback
image   : Gazebo 8.15.0 · ros_gz 1.0.24 · ros2_control 4.48.0 · MoveIt 2.12.4 · gz_ros2_control 1.2.20
build   : colcon 3 paquets (18,8 s) · URDF 11/11 · garde-fous 7/7 · ruff « All checks passed! »
gazebo  : debout 10 s (z=1,065) · squat 0,031 rad · RTF 0.50 (sans) / 0.60 (caméra+IMU) · /camera/* publiés
mcp     : tools/list 5/5 · appels réels blender/freecad/ros2 · bag v9 lu par rosbags (17 656 msgs)
e2e     : E2E_OK 1/3 — STEP/STL/BLEND/GLB + bag + diagnostic effort 0,055 Nm ; journal 44 entrées
e2e (2) : E2E_OK après rebuild (anyio) — bag 11 526 msgs (/clock 8 882, /imu 1 766), z=1,0558 m, effort max 0,0554 Nm, 4/4 critères
tests   : docs/TESTING.md — procédure de validation à 6 niveaux (prérequis → CI), commandes et résultats attendus mesurés
trivy   : image dronecad/ros2-jazzy:0.1.0 → 0 HIGH/CRITICAL corrigeable (local, 0.74.0) ; CI : image propre après bump anyio (CVE-2026-63374)
ci      : run 35418441478 → validate ✅ lint ✅ container-tests ✅ (colcon + fumée Gazebo + debout dans l'image + Trivy) secret-scan ✅
ollama  : gpt-oss:20b 100% GPU ctx 8192 — 115,44 tok/s · 1 463 Mio libres
releases: v0.1.0 · v0.2.0 (vérifiées) · [Unreleased] prêt pour la prochaine coupe full-auto (v0.3.0)
```

## En attente / prochaines actions (aucun TODO silencieux)

- **Réglé le 2026-09-19** : la mémoire cognitive fonctionne **sans clé tierce** — `SHODH_API_KEYS` est une clé que l'on génère pour son propre serveur local (`varunshodh/shodh-memory`), documentée dans `.env.example`, injectée par le compose, expansée par `.mcp.json` (jamais versionnée). Appels réels vérifiés : `memory_stats`, `remember`, `recall` (95 %).
- **Utilisateur** : enregistrement des serveurs MCP dans Kimi Code (il ne lit pas `.mcp.json` nativement) — les 5 entrées sont à recopier depuis `.mcp.json`.
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
| ~22:00–23:20 | **CI verte** (run `35418441478`) après cinq runs rouges : `EXE001` (chmod Windows), course du spawn → `spawn_ready.py`, monde OGRE2 → `flat_ground_headless.sdf`, **uid 1001 sans entrée passwd → gz-transport muet**, CVE CRITICAL `anyio` corrigée ; instrumentation du test et étape de fumée ajoutées |
| ~23:30–00:10 | Conteneur recréé sur l'image à jour (anyio 4.15.1, uid 1000) ; **boucle E2E re-mesurée `E2E_OK`** (11 526 msgs, z = 1,0558 m, effort 0,0554 Nm) ; garde-fou `${VAR}` non définie dans le client MCP ; `docs/TESTING.md` (procédure de test) |
| ~01:45–02:05 | **Mémoire cognitive rendue opérationnelle sans clé tierce** : `.env` (ignoré) + `.env.example`, `SHODH_API_KEYS` injectée par le compose, `.mcp.json` expansé côté client ; appels réels `memory_stats` / `remember` / `recall` (95 %) ; `agent/mcp_call.py` en UTF-8 (consoles cp1252) ; `docs/USAGE.md` (mode d'emploi) |
