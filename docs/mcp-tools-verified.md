# MCP servers — vérification complète (Phase 3)

> Preuves datées du **2026-09-18/19**, obtenues via `python agent/agent_loop.py --list-tools <serveur>`
> et `python agent/mcp_call.py <serveur> <outil>` (client stdio maison JSON-RPC 2.0, `agent/mcp_stdio.py`
> — aucun SDK externe). EN: dated evidence per MCP server — tool lists AND live tool calls.
> FR : preuves datées par serveur MCP — listes d'outils **et** appels d'outils réels.

## `tools/list` — 5/5 serveurs ✅

| Serveur | Statut | Outils | Extrait (noms réels) |
|---|---|---|---|
| `blender` — `uvx mcp-for-blender` (addon v1.7 activé, Blender 5.2, socket 9876) | ✅ | **31** | `get_scene_info`, `get_addon_status`, `execute_blender_code`, `export_scene`, `get_viewport_screenshot`, … |
| `freecad` — `uvx --from freecad-robust-mcp --with 'mcp<2' freecad-mcp` (mode xmlrpc, FreeCAD 1.1.3, bridge auto-démarré `AutoStart`, XML-RPC 9875, socket 9877) | ✅ | **83** | `create_document`, `create_sketch`, `add_sketch_rectangle`, `pad_sketch`, `export_step`, `get_screenshot`, `list_documents`, … |
| `ros2` — `docker exec dronecad-ros2-jazzy … /opt/ros2-mcp/.venv/bin/mcp_ros_2_server` (tag `2606`, venv python 3.12) | ✅ | **20** | `ros2_topic_list`, `ros2_topic_publish`, `ros2_service_call`, `ros2_send_action_goal`, `ros2_stream_*`, … |
| `rosbags` — `vendor/mcp-rosbags/.venv/Scripts/python.exe scripts/rosbags_mcp_server.py` (sous-module épinglé + **wrapper de compat** : rosbags moderne pour les bags Jazzy v9, shim `deserialize_cdr`/`serialize_cdr`, `mcp<2`) | ✅ vérifié | **15** | `set_bag_path`, `bag_info`, `get_messages_in_range`, `analyze_trajectory`, `plot_timeseries`, `get_tf_tree`, … — **lecture réelle d'un bag mcap v9** (17 656 messages) |
| `memory` — `npx -y @shodh/memory-mcp` v0.2.0 + `SHODH_API_URL=http://127.0.0.1:3030`, `SHODH_API_KEY=${SHODH_API_KEYS}` (clé **locale choisie par l'utilisateur**, service `dronecad-shodh-memory`, volume `shodh-data`) | ✅ | **38** | `remember`, `recall`, `recall_by_tags`, `context_summary`, todos/projets, `backup_*`, … |

## Appels d'outils réels (chaîne complète prouvée)

| Appel | Résultat |
|---|---|
| `blender get_scene_info` | ✅ **scène vivante** : `{"user_prompt": "…"}` (l'addon exige ce champ depuis sa mise à jour — un appel sans argument renvoie une erreur de validation pydantic) → 4 objets (`Light`, `Camera`, …), lu depuis la Blender GUI ouverte (socket 9876) |
| `freecad get_freecad_version` | ✅ **instance vivante** : FreeCAD **1.1.3**, build 20260725, `gui_available: 1` (XML-RPC 9875) |
| `ros2 ros2_topic_list` | ✅ **graphe ROS 2 vivant** dans le conteneur (`/parameter_events`, types réels) |
| `memory memory_stats` · `remember` · `recall` | ✅ **mémoire locale opérationnelle** — clé générée dans `.env` (aucun abonnement tiers) : `memory_stats` → « 🐘 Memory Statistics v0.2.0 » ; cycle `remember` → `recall` vérifié le 2026-09-19 (**95 % de pertinence**, identifiant persistant) |
| `rosbags` appels | ✅ appels directs vérifiés : `set_bag_path {"path": …}` → `success: true`, `mcap_files: 1`, puis `bag_info {"bag_path": …}` sur le sac réel de la boucle E2E (**11 526 messages**, `/clock` 8 882, `/imu` 1 766, `/joint_states` 878) |

## Notes d'intégration (rencontrées et documentées)

- **`mcp<2` obligatoire** pour le client freecad-robust-mcp (métadonnées amont autorisent `mcp` 2.x, qui a renommé `FastMCP` → `ModuleNotFoundError`).
- **`rosbags<0.10` obligatoire** pour mcp-rosbags (dépôt stale d'1 an : `from rosbags.serde import deserialize_cdr` supprimé des versions récentes) — **candidat fork** confirmé.
- **Ports séparés** : FreeCAD XML-RPC 9875 + socket 9877 (`SocketPort`, déplacé) ; Blender addon 9876 — plus de collision.
- **uv + Windows** : création de « trampoline » PE dans `%TEMP%` refusée une fois (AV/SAC probable) — retry OK ; si récidive, contournement `pip --target` documenté au besoin.
- **Kimi Code** : ne lit pas `.mcp.json` nativement — l'enregistrement côté client reste à faire (Claude Code / Cursor lisent le fichier tel quel).
