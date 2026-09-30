# Verified MCP tools

All five servers in `.mcp.json` were checked with a real `tools/list` call and live tool calls.

## Servers

| Server | Command | Tools | Examples |
|---|---|---|---|
| `blender` | Blender MCP add-on v1.7 on port 9876 | 31 | `get_scene_info`, object and material tools |
| `freecad` | `uvx --from freecad-robust-mcp --with 'mcp<2' freecad-mcp` (xmlrpc mode, FreeCAD 1.1.3, bridge auto-started on 9875 and 9877) | 83 | `create_document`, `create_sketch`, `add_sketch_rectangle`, `pad_sketch`, `export_step`, `get_screenshot` |
| `ros2` | `docker exec dronecad-ros2-jazzy ... mcp_ros_2_server` (Python 3.12 virtual environment) | 20 | `ros2_topic_list`, `ros2_topic_publish`, `ros2_service_call`, `ros2_send_action_goal` |
| `rosbags` | Pinned submodule in `vendor/mcp-rosbags` with a compatibility wrapper (modern `rosbags` for Jazzy v9 bags, `mcp<2`) | 15 | `set_bag_path`, `bag_info`, `get_messages_in_range`, `analyze_trajectory`, `plot_timeseries`, `get_tf_tree` |
| `memory` | `npx -y @shodh/memory-mcp` v0.2.0 with `SHODH_API_URL=http://127.0.0.1:3030` and `SHODH_API_KEY=${SHODH_API_KEYS}` | 38 | `remember`, `recall`, `recall_by_tags`, `context_summary`, todos, backups |

The memory key is one you choose for your own local server. It is not a third-party subscription.

## Live calls

| Call | Result |
|---|---|
| `blender get_scene_info` | Live scene read from the open Blender GUI. Note: it now requires a `user_prompt` argument. |
| `freecad get_freecad_version` | FreeCAD 1.1.3 with `gui_available: 1`. |
| `ros2 ros2_topic_list` | Live ROS 2 graph inside the container. |
| `memory memory_stats`, `remember`, `recall` | Local memory operational. `recall` returned the stored note at 95% relevance with a persistent ID. |
| `rosbags set_bag_path` and `bag_info` | Read the real bag from the end-to-end loop: 11,526 messages, `/clock` 8,882, `/imu` 1,766, `/joint_states` 878. |
