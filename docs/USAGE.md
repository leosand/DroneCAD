# Usage guide

Day-to-day usage: start the stack, connect an MCP client, drive the simulation, run the agent loop, use the memory. Commands are shown for Windows PowerShell, the platform the host-side bridges were verified on.

## 1. Start the stack

```powershell
cd <path-to-DroneCAD>
$env:DRONECAD_HOME  = (Get-Location).Path        # required by the rosbags MCP entry
$env:SHODH_API_KEYS = (Get-Content .env | Select-String '^SHODH_API_KEYS=').Line.Split('=')[1]

docker compose up -d        # ros2-jazzy (ROS 2 + Gazebo + MoveIt 2) and shodh-memory
docker compose ps           # both services must be Up
python scripts\validate_stack.py
```

The model server is `gpt-oss:20b` on port 11499. `scripts\start-ollama-gptoss.ps1` starts it if it is not running. FreeCAD and Blender must be open on the host; their bridges listen on loopback only (FreeCAD 9875 and 9877, Blender 9876).

First time only: `cp .env.example .env`, then generate the memory key with `python -c "import secrets; print(secrets.token_hex(24))"`.

## 2. Connect an MCP client

`.mcp.json` is the canonical registry of the five servers.

| Client | What to do |
|---|---|
| Claude Code | Open the project folder. It reads `.mcp.json` and asks for approval. |
| Cursor | Copy the entries into `~/.cursor/mcp.json`. |
| Kimi Code | It does not read `.mcp.json`. Copy the five entries into its MCP configuration. |

Servers and tool counts: `blender` 31, `freecad` 83, `ros2` 20, `rosbags` 15, `memory` 38. Quick check without a graphical client:

```powershell
python agent\mcp_call.py blender get_scene_info '{"user_prompt": "Describe the scene"}'
python agent\mcp_call.py freecad get_freecad_version
python agent\mcp_call.py ros2 ros2_topic_list
```

## 3. Drive the simulation

Terminal 1 starts the simulation (Gazebo server, robot and ROS-Gazebo bridge):

```powershell
docker exec -it dronecad-ros2-jazzy bash -lc "source /opt/ros/jazzy/setup.bash && source /workspace/install/setup.bash && ros2 launch humanoid_gazebo sim.launch.py"
```

Terminal 2 observes and commands:

```powershell
docker exec -it dronecad-ros2-jazzy bash -lc "source /opt/ros/jazzy/setup.bash && source /workspace/install/setup.bash && ros2 topic echo /joint_states --once"
docker exec -it dronecad-ros2-jazzy bash -lc "source /opt/ros/jazzy/setup.bash && source /workspace/install/setup.bash && ros2 topic pub --once /joint_position_controller/commands std_msgs/msg/Float64MultiArray '{data: [0.3,0.3,0,0,0,0,0,0,0,0,0,0]}'"
docker exec -it dronecad-ros2-jazzy bash -lc "source /opt/ros/jazzy/setup.bash && source /workspace/install/setup.bash && ros2 bag record -o /artifacts/my_bag /clock /joint_states"
```

`sim.launch.py` accepts `world_file:=obstacles.sdf` for obstacles and `enable_camera:=true` for an RGB-D camera plus IMU.

## 4. Query a recorded bag

The `rosbags` server runs on the host, so pass a host path.

```powershell
python agent\mcp_call.py rosbags set_bag_path '{"path": "<path-to-DroneCAD>/artifacts/my_bag"}'
python agent\mcp_call.py rosbags bag_info '{"bag_path": "<path-to-DroneCAD>/artifacts/my_bag"}'
```

Example real output: 11,526 messages, `/clock` 8,882 at 433 Hz, `/imu` 1,766, `/joint_states` 878. That is enough to ask an agent whether the robot fell and what the peak effort was.

## 5. Run the full agent loop

```powershell
python scripts\e2e_bracket.py     # design, model, simulate, analyze, iterate
```

Expected result: `E2E_OK` within three iterations. `artifacts/` then holds the bracket STEP and STL (FreeCAD), the master BLEND and GLB (Blender), the rosbag2 recording and the diagnostic (`no_fall`, `effort_within_limits`). The correlated journal is `artifacts/e2e_journal.jsonl`.

## 6. Use the memory

```powershell
python agent\mcp_call.py memory remember '{"content": "a decision or fact to keep", "tags": ["dronecad"]}'
python agent\mcp_call.py memory recall '{"query": "why the standing test needs uid 1000"}'
python agent\mcp_call.py memory memory_stats
```

The memory is local: container `dronecad-shodh-memory`, volume `shodh-data`, port `127.0.0.1:3030`. It is protected by your own key (`SHODH_API_KEYS` in `.env`, never committed). A `remember` followed by a `recall` returns the note with a stable ID.

## 7. Stop and clean up

```powershell
docker compose stop        # keeps data
docker compose down        # removes containers, keeps volumes
docker compose down -v     # also deletes the memory and data volumes
```

## 8. Troubleshooting

| Symptom | Fix |
|---|---|
| Executable not found mentioning `${DRONECAD_HOME}` | Set `DRONECAD_HOME` (section 1). |
| `503 AUTH_NOT_CONFIGURED` from `memory` | The key is empty or out of sync. Fill `.env`, run `docker compose up -d --force-recreate shodh-memory`, export the variable. |
| The robot never appears | The container runs as a user ID missing from `/etc/passwd`. Use `--user 1000:1000`. |
| FreeCAD or Blender unreachable | Reopen the host GUI and check ports 9875 and 9876. |
| Console crashes on an emoji | `agent/mcp_call.py` forces UTF-8. Set `PYTHONIOENCODING=utf-8` as a fallback. |

For the full validation procedure see [TESTING.md](TESTING.md).
