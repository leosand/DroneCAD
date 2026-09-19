# MCP servers — `tools/list` vérifiés (Phase 3)

> Preuves datées du **2026-09-18**, obtenues via `python agent/agent_loop.py --list-tools <serveur>`
> (client stdio maison JSON-RPC 2.0, `agent/mcp_stdio.py` — aucun SDK externe).
> EN: dated evidence of a real `tools/list` round-trip per server. / FR : preuves datées d'un
> aller-retour `tools/list` réel par serveur.

| Serveur | Statut | Outils | Extrait (noms réels) |
|---|---|---|---|
| `blender` — `uvx mcp-for-blender` | ✅ vérifié | **31** | `get_scene_info`, `execute_blender_code`, `export_scene`, `get_viewport_screenshot`, `download_sketchfab_model`, … |
| `memory` — `npx -y @shodh/memory-mcp` (v0.2.0) | ✅ vérifié | **38** | `remember`, `recall`, `recall_by_tags`, `context_summary`, `set_reminder`, todos/projets, `backup_*`, … |
| `freecad` — `uvx --from freecad-robust-mcp --with 'mcp<2' freecad-mcp` | ⏳ en attente | — | exige le serveur XML-RPC du workbench « Robust MCP Bridge » **démarré dans FreeCAD** (`127.0.0.1:9875`). Diagnostic : le serveur ne répond pas à `initialize` tant que le pont n'est pas actif. |
| `ros2` — `docker exec dronecad-ros2-jazzy … /opt/ros2-mcp/.venv/bin/mcp_ros_2_server` (vendored, tag `2606`, venv **python 3.12 système**) | ✅ vérifié | **20** | `ros2_topic_list`, `ros2_topic_publish`, `ros2_service_call`, `ros2_send_action_goal`, `ros2_stream_*`, … |
| `rosbags` — `binabik-ai/mcp-rosbags` (clone vendor) | ⏳ Phase 3 | — | dépôt stale (1 an) → décision fork ; clone + `requirements.txt` à faire |

## Allowlist mise à jour

`agent/tool_allowlist.json` : `blender` et `memory` figés avec les **noms réels** ci-dessus
(sous-ensembles pertinents) ; `memory` (mémoire cognitive) est autorisé dans toutes les phases.
Les serveurs non vérifiés restent **volontairement vides** — le garde refuse tout appel absent.
