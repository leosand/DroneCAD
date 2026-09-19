# TESTING.md — DroneCAD : valider la pile soi-même / validate the stack yourself

> EN: every command below was executed on the target workstation (RTX 4070 Ti SUPER, Windows +
>     Docker Desktop/WSL2, Blender 5.2, FreeCAD 1.1.3) on **2026-09-19**; the expected outputs are
>     the measured ones, not approximations.
> FR-CA : chaque commande ci-dessous a été exécutée sur la station cible (RTX 4070 Ti SUPER,
>     Windows + Docker Desktop/WSL2, Blender 5.2, FreeCAD 1.1.3) le **2026-09-19** ; les résultats
>     attendus sont ceux mesurés, pas des approximations.

---

## 0. Prérequis (2 min) / Prerequisites

```powershell
# EN: the MCP registry uses ${DRONECAD_HOME} for the vendored rosbags server — without it the
#     tool now fails with an explicit message instead of a bare "file not found".
# FR : le registre MCP utilise ${DRONECAD_HOME} pour le serveur rosbags vendoré — sans elle,
#     l'outil échoue désormais avec un message explicite plutôt qu'un « fichier introuvable » nu.
$env:DRONECAD_HOME = "E:\Mes apps\DroneCAD"
# EN: cognitive-memory key — YOUR key for YOUR local server (cp .env.example .env, first time only)
# FR : clé de la mémoire cognitive — la VÔTRE, pour votre serveur local (cp .env.example .env, une fois)
$env:SHODH_API_KEYS = (Get-Content .env | Select-String '^SHODH_API_KEYS=').Line.Split('=')[1]
cd $env:DRONECAD_HOME

docker info --format '{{.ServerVersion}}'          # Docker Desktop démarré / running
tasklist | findstr /I "FreeCAD.exe blender.exe"    # les 2 GUI ouvertes / both GUIs open
curl http://127.0.0.1:11499/api/version            # serveur Ollama dédié / dedicated server
```

Ponts MCP hôte attendus (loopback seulement) : FreeCAD ≈ `127.0.0.1:9875` (XML-RPC) et `:9877`
(socket addon), Blender `127.0.0.1:9876`. Le serveur de modèle est `gpt-oss:20b` sur `:11499`
(`scripts/start-ollama-gptoss.ps1` le démarre si besoin).

---

## 1. 30 s — la pile répond / the stack answers

```powershell
docker compose config -q          # aucune sortie, code 0 / no output, exit 0
python scripts\validate_stack.py  # ports loopback seuls, pas de privileged, pas de secret
docker compose up -d              # ros2-jazzy + shodh-memory
docker exec dronecad-ros2-jazzy id -u   # attendu / expected: 1000  (non-root)
```

## 2. 1 min — lint + garde-fous agentiques / lint + agent guards

```powershell
ruff check agent scripts ws/src                 # attendu / expected: All checks passed!
python -m pytest agent\tests -q                 # attendu / expected: 7 passed
```

Les 11 tests URDF complets (dont `check_urdf`) demandent `xacro` : la CI les exécute dans l'image
livrée (job `container-tests`). En local, ils sont *skipped* sans `xacro` — c'est normal.

## 3. 3 min — le robot tient debout 10 s simulées / the robot stands (the flagship test)

```powershell
docker run --rm --network host --user 1000:1000 --shm-size=1g `
  -e HOME=/tmp -e ROS_LOG_DIR=/tmp/ros_logs `
  -v "${PWD}\ws:/workspace:ro" dronecad/ros2-jazzy:0.1.0 `
  bash -lc "source /opt/ros/jazzy/setup.bash && source /workspace/install/setup.bash && cd /workspace && python3 -m pytest src/humanoid_gazebo/test/test_stand.py -q -s -o cache_dir=/tmp/.pytest_cache"
```

Attendu / expected :

```text
[spawn_ready] serveur Gazebo prêt après 2.2 s
[test_stand] OK — z=1.065 m, roll=0.000, pitch=-0.000 après 10 s simulées
1 passed in ~38 s
```

> **`--user 1000:1000` n'est pas décoratif.** Un uid absent de `/etc/passwd` de l'image rend
> gz-transport totalement muet (le serveur démarre, s'initialise, et n'annonce aucun topic) —
> c'est la cause racine de cinq runs CI rouges, documentée dans `REPORT.md` § écarts 17.

## 4. 2 min — les 5 serveurs MCP / the 5 MCP servers

```powershell
python agent\mcp_call.py blender get_scene_info       # scène vivante / live scene (3 objets)
python agent\mcp_call.py freecad get_freecad_version  # FreeCAD 1.1.3, gui_available: 1
python agent\mcp_call.py ros2 ros2_topic_list         # graphe ROS 2 du conteneur / container graph
python agent\mcp_call.py rosbags set_bag_path '{"path": "E:/Mes apps/DroneCAD/artifacts/e2e_bag"}'
python agent\mcp_call.py memory memory_stats          # mémoire locale / local memory (🐘 v0.2.0)
```

`tools/list` est le contrôle minimal pour chacun : `31 / 83 / 20 / 15 / 38` outils
(`docs/mcp-tools-verified.md`). Le serveur `rosbags` passe par le venv vendoré et le wrapper de
compatibilité (bags Jazzy v9). La mémoire est **locale** et protégée par **votre** clé : la
générer dans `.env` (`python -c "import secrets; print(secrets.token_hex(24))"`, voir
`.env.example`), puis `docker compose up -d --force-recreate shodh-memory`. Cycle vérifié :
`remember` puis `recall` → **95 % de pertinence**, identifiant persistant.

## 5. 5-10 min — la boucle agentique complète / the full agentic loop

```powershell
python scripts\e2e_bracket.py
```

Attendu / expected : `E2E_OK` en 1 itération (sur 3 autorisées) — équerre paramétrique FreeCAD →
STEP/STL → Blender `.blend` + GLB → Gazebo headless avec commande squat publiée **par MCP** →
rosbag2 (11 500 à 17 700 messages selon la durée d'enregistrement) → diagnostic rosbags
(`no_fall`, `effort_within_limits` vrais). Artefacts dans `artifacts/`, journal JSONL
`artifacts/e2e_journal.jsonl` (allowlist, timeout par appel, corrélation).

Mesure de référence (2026-09-19, après rebuild de l'image) : 11 526 messages
(`/clock` 8 882, `/imu` 1 766), **z = 1,0558 m**, effort articulaire max **0,0554 Nm**, `E2E_OK`.

## 6. CI, releases, sécurité / CI, releases, security

```powershell
gh run list -R leosand/DroneCAD --limit 3      # attendu / expected: 4 jobs verts
gh release list -R leosand/DroneCAD            # v0.1.0 / v0.2.0 (pré-releases)
# Scan d'image local (la CI reste la source de vérité : sa base de vulnérabilités est plus fraîche)
# Premier lancement : téléchargement de la base + analyse d'une image de 6,3 Go → plusieurs minutes.
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock `
  ghcr.io/aquasecurity/trivy:0.74.0 image --severity HIGH,CRITICAL --ignore-unfixed dronecad/ros2-jazzy:0.1.0
# attendu / expected: aucun constat HIGH/CRITICAL corrigeable, code de sortie 0 (mesuré le 2026-09-19)
```

## Que faire si ça échoue / When it fails

| Symptôme | Cause | Geste |
|---|---|---|
| `exécutable introuvable … ${DRONECAD_HOME}` | variable non définie | la définir (§0) puis relancer |
| `le robot n'est jamais apparu` | conteneur lancé avec un uid absent de `/etc/passwd` | `--user 1000:1000` |
| `gz topic -l` vide dans le conteneur | même cause | idem |
| FreeCAD/Blender : timeout MCP | GUI fermée ou addon non chargé | rouvrir la GUI, vérifier `:9875`/`:9876` |
| `memory` : `503 AUTH_NOT_CONFIGURED` | clé vide ou désynchronisée | générer **votre** clé dans `.env` (voir `.env.example`), recréer le service, exporter la variable |
| CI rouge à l'étape Trivy | lire le message : `no space left on device` ≠ vulnérabilité | voir `REPORT.md` § *Porte qualité CI* |
| Test debout lent (> 2 min) | CPU partagé, RTF < 1 | normal : le test compte le **temps simulé**, pas le temps mural |

## Ce que « parfaitement testé » signifie ici / What "fully tested" means here

1. la pile démarre et reste non-root, sans port public ;
2. le robot tient 10 s simulées **dans l'image livrée** (en local **et** en CI) ;
3. les 5 serveurs MCP répondent avec des appels réels, pas seulement `tools/list` ;
4. la boucle agentique produit ses artefacts de bout en bout, garde-fous actifs ;
5. la CI est verte (4 jobs) et le scan d'image ne laisse aucune vulnérabilité HIGH/CRITICAL
   corrigeable ;
6. tout écart restant est écrit dans `REPORT.md` — aucun « TODO » silencieux.
