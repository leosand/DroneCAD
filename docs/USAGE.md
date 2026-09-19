# USAGE.md — DroneCAD : mode d'emploi / how to use it

> EN: day-to-day usage — start the stack, plug an MCP client, drive the simulation, run the agentic
>     loop, use the cognitive memory. Every command below was run on the workstation on 2026-09-19.
> FR-CA : usage quotidien — démarrer la pile, brancher un client MCP, piloter la simulation, lancer
>     la boucle agentique, utiliser la mémoire cognitive. Chaque commande a été exécutée sur la
>     station le 2026-09-19.

---

## 1. Démarrer la pile / start the stack

```powershell
cd "E:\Mes apps\DroneCAD"
$env:DRONECAD_HOME  = "E:\Mes apps\DroneCAD"     # requis par l'entrée MCP « rosbags »

docker compose up -d            # ros2-jazzy (ROS 2 + Gazebo + MoveIt 2) + shodh-memory
docker compose ps               # les deux services doivent être « Up » / both must be « Up »
python scripts\validate_stack.py
```

La clé de mémoire vit dans `.env` et **les scripts du dépôt la lisent tout seuls** : rien à
exporter. Seuls les clients MCP externes (Claude Code, Cursor) ont besoin de `SHODH_API_KEYS`
dans leur propre environnement, puisqu'ils expansent `${SHODH_API_KEYS}` eux-mêmes.

Le serveur de modèle est `gpt-oss:20b` sur `:11499` : `scripts\start-ollama-gptoss.ps1` le démarre
s'il ne tourne pas. Côté hôte, FreeCAD et Blender doivent être **ouverts** (ponts MCP en loopback
seulement : FreeCAD `:9875`/`:9877`, Blender `:9876`).

Première fois seulement : `cp .env.example .env` puis générer la clé de mémoire
(`python -c "import secrets; print(secrets.token_hex(24))"`).

## 2. Brancher un client MCP / plug an MCP client

`.mcp.json` est le registre canonique (5 serveurs) :

| Client | Geste |
|---|---|
| **Claude Code** | ouvrir le dossier du projet : il lit `.mcp.json` et demande l'approbation |
| **Cursor** | mêmes entrées à recopier dans `~/.cursor/mcp.json` |
| **Kimi Code** | ne lit pas `.mcp.json` : recopier les 5 entrées dans sa configuration MCP |

Les serveurs : `blender` (31 outils), `freecad` (83), `ros2` (20), `rosbags` (15), `memory` (38).
Vérification sans client graphique :

```powershell
python agent\mcp_call.py blender get_scene_info        # scène Blender vivante
python agent\mcp_call.py freecad get_freecad_version   # FreeCAD 1.1.3
python agent\mcp_call.py ros2 ros2_topic_list          # graphe ROS 2 du conteneur
```

## 3. Piloter la simulation / drive the simulation

```powershell
# Terminal 1 — la simulation (serveur Gazebo + robot + pont ROS ↔ Gazebo)
docker exec -it dronecad-ros2-jazzy bash -lc "source /opt/ros/jazzy/setup.bash && source /workspace/install/setup.bash && ros2 launch humanoid_gazebo sim.launch.py"
```

```powershell
# Terminal 2 — observer et commander
docker exec -it dronecad-ros2-jazzy bash -lc "source /opt/ros/jazzy/setup.bash && source /workspace/install/setup.bash && ros2 topic echo /joint_states --once"
docker exec -it dronecad-ros2-jazzy bash -lc "source /opt/ros/jazzy/setup.bash && source /workspace/install/setup.bash && ros2 topic pub --once /joint_position_controller/commands std_msgs/msg/Float64MultiArray '{data: [0.3,0.3,0,0,0,0,0,0,0,0,0,0]}'"
docker exec -it dronecad-ros2-jazzy bash -lc "source /opt/ros/jazzy/setup.bash && source /workspace/install/setup.bash && ros2 bag record -o /artifacts/mon_sac /clock /joint_states"
```

`sim.launch.py` accepte `world_file:=obstacles.sdf` (obstacles) et `enable_camera:=true`
(caméra RGB-D + IMU ; RTF mesuré 0,60 sur le Xeon 4 cœurs).

## 4. Interroger un sac d'enregistrement / query a recording

Le serveur `rosbags` tourne **sur l'hôte** : donner un chemin **Windows**.

```powershell
python agent\mcp_call.py rosbags set_bag_path '{"path": "E:/Mes apps/DroneCAD/artifacts/mon_sac"}'
python agent\mcp_call.py rosbags bag_info '{"bag_path": "E:/Mes apps/DroneCAD/artifacts/mon_sac"}'
```

Exemple de sortie réelle : `message_count: 11526`, `/clock` 8 882 msgs à 433 Hz, `/imu` 1 766,
`/joint_states` 878 — de quoi demander à un agent « le robot a-t-il chuté ? quel effort max ? ».

## 5. Lancer la boucle agentique complète / run the full agentic loop

```powershell
python scripts\e2e_bracket.py                 # concevoir → modéliser → simuler → analyser → itérer
```

Résultat attendu : `E2E_OK` (1 itération sur 3 maximum) avec, dans `artifacts/`, le STEP/STL de
l'équerre (FreeCAD), le `.blend` maître + GLB (Blender), le sac rosbag2 et le diagnostic
(`no_fall`, `effort_within_limits`). Journal corrélé : `artifacts/e2e_journal.jsonl`
(allowlist d'outils par phase, timeout par appel, identifiant de corrélation).

## 6. Mémoire cognitive / cognitive memory

```powershell
python agent\mcp_call.py memory remember '{"content": "décision ou fait à retenir", "tags": ["dronecad"]}'
python agent\mcp_call.py memory recall   '{"query": "pourquoi le test debout exige uid 1000"}'
python agent\mcp_call.py memory memory_stats
```

Elle est **locale** (conteneur `dronecad-shodh-memory`, volume `shodh-data`, port `127.0.0.1:3030`)
et protégée par **votre** clé (`SHODH_API_KEYS` dans `.env`, jamais versionnée). Persistance
vérifiée : un `remember` puis un `recall` retrouvent la note avec son identifiant stable.

## 7. Arrêter, nettoyer / stop, clean

```powershell
docker compose stop            # garde les données / keeps data
docker compose down            # supprime les conteneurs / removes containers (volume conservé)
docker compose down -v         # ⚠️ supprime aussi la mémoire et les données / also deletes memory
```

## 8. Dépannage express / quick troubleshooting

| Symptôme | Geste |
|---|---|
| `exécutable introuvable … ${DRONECAD_HOME}` | définir `DRONECAD_HOME` (§1) |
| `503 AUTH_NOT_CONFIGURED` sur `memory` | `SHODH_API_KEYS` vide ou désynchronisée : renseigner `.env`, `docker compose up -d --force-recreate shodh-memory`, exporter la variable |
| `le robot n'est jamais apparu` | conteneur lancé avec un uid absent de `/etc/passwd` → `--user 1000:1000` |
| FreeCAD/Blender injoignables | rouvrir la GUI hôte, vérifier `:9875` / `:9876` |
| Console Windows qui plante sur un emoji | `agent/mcp_call.py` force désormais l'UTF-8 (`PYTHONIOENCODING=utf-8` en secours) |

Pour la validation complète (6 niveaux, de 30 s à 10 min), voir [`TESTING.md`](TESTING.md) ;
pour l'état des phases et les écarts assumés, voir [`../REPORT.md`](../REPORT.md).
