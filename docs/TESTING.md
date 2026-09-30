# Testing guide

A six-level procedure to validate the stack yourself, from a 30-second check to the full 10-minute agent loop. Expected outputs are measured values from the reference workstation (NVIDIA RTX 4070 Ti SUPER, Windows with Docker Desktop and WSL2, Blender 5.2, FreeCAD 1.1.3). Commands use Windows PowerShell.

## 0. Prerequisites (2 min)

```powershell
$env:DRONECAD_HOME = "<path-to-DroneCAD>"     # required by the rosbags MCP entry
cd $env:DRONECAD_HOME
$env:SHODH_API_KEYS = (Get-Content .env | Select-String '^SHODH_API_KEYS=').Line.Split('=')[1]

docker info --format '{{.ServerVersion}}'          # Docker is running
tasklist | findstr /I "FreeCAD.exe blender.exe"    # both GUIs are open
curl http://127.0.0.1:11499/api/version            # dedicated Ollama server
```

Expected host bridges (loopback only): FreeCAD on 9875 (XML-RPC) and 9877 (socket), Blender on 9876. The model server is `gpt-oss:20b` on port 11499; `scripts\start-ollama-gptoss.ps1` starts it if needed. Without `DRONECAD_HOME`, the tool now fails with an explicit message.

## 1. 30 seconds: the stack answers

```powershell
docker compose config -q                 # no output, exit code 0
python scripts\validate_stack.py         # loopback ports only, no privileged, no secrets
docker compose up -d                     # ros2-jazzy and shodh-memory
docker exec dronecad-ros2-jazzy id -u    # expected: 1000 (non-root)
```

## 2. 1 minute: lint and agent guardrails

```powershell
ruff check agent scripts ws/src          # expected: All checks passed!
python -m pytest agent\tests -q          # expected: 7 passed
```

The 11 URDF tests (including `check_urdf`) need `xacro`. CI runs them in the delivered image (`container-tests` job). Locally they are skipped without `xacro`, which is normal.

## 3. 3 minutes: the robot stands for 10 simulated seconds

```powershell
docker run --rm --network host --user 1000:1000 --shm-size=1g `
  -e HOME=/tmp -e ROS_LOG_DIR=/tmp/ros_logs `
  -v "${PWD}\ws:/workspace:ro" dronecad/ros2-jazzy:<tag> `
  bash -lc "source /opt/ros/jazzy/setup.bash && source /workspace/install/setup.bash && cd /workspace && python3 -m pytest src/humanoid_gazebo/test/test_stand.py -q -s -o cache_dir=/tmp/.pytest_cache"
```

Expected:

```text
[spawn_ready] Gazebo server ready after 2.2 s
[test_stand] OK: z=1.065 m, roll=0.000, pitch=-0.000 after 10 s simulated
1 passed in ~38 s
```

`--user 1000:1000` is required. A user ID missing from the image's `/etc/passwd` makes gz-transport silent: the server starts and announces no topic. This was the root cause of five red CI runs.

## 4. 2 minutes: the five MCP servers

```powershell
python agent\mcp_call.py blender get_scene_info '{"user_prompt": "Describe the scene"}'
python agent\mcp_call.py freecad get_freecad_version      # FreeCAD 1.1.3, gui_available: 1
python agent\mcp_call.py ros2 ros2_topic_list             # container ROS 2 graph
python agent\mcp_call.py rosbags set_bag_path '{"path": "<path-to-DroneCAD>/artifacts/e2e_bag"}'
python agent\mcp_call.py memory memory_stats              # local memory, v0.2.0
```

`tools/list` is the minimal check for each server: 31, 83, 20, 15 and 38 tools (see [mcp-tools-verified.md](mcp-tools-verified.md)). The memory is local and protected by your own key: generate it in `.env` with `python -c "import secrets; print(secrets.token_hex(24))"`, then run `docker compose up -d --force-recreate shodh-memory`. A `remember` followed by a `recall` returned 95% relevance with a persistent ID.

## 5. 5 to 10 minutes: the full agent loop

```powershell
python scripts\e2e_bracket.py
```

Expected: `E2E_OK` in one iteration (three allowed). A parametric FreeCAD bracket becomes STEP and STL files, then a Blender `.blend` and GLB. Gazebo runs headless with a squat command published through MCP and records a rosbag2 (11,500 to 17,700 messages depending on duration). The rosbags diagnostic reports `no_fall` and `effort_within_limits` as true. Artifacts are in `artifacts/`; the JSONL journal is `artifacts/e2e_journal.jsonl`.

Reference measurement: 11,526 messages (`/clock` 8,882, `/imu` 1,766), z = 1.0558 m, peak joint effort 0.0554 Nm.

## 6. CI, releases and security

```powershell
gh run list -R <owner>/DroneCAD --limit 3       # expected: all jobs green
gh release list -R <owner>/DroneCAD
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock `
  ghcr.io/aquasecurity/trivy:0.74.0 image --severity HIGH,CRITICAL --ignore-unfixed dronecad/ros2-jazzy:<tag>
```

CI stays the source of truth: its vulnerability database is fresher. The first local Trivy run downloads the database and scans a 6.3 GB image, and needs about 20 GB of temporary space.

## When it fails

| Symptom | Cause | Fix |
|---|---|---|
| Executable not found mentioning `${DRONECAD_HOME}` | Variable not set | Set it (section 0). |
| The robot never appears | Container user ID missing from `/etc/passwd` | Use `--user 1000:1000`. |
| `gz topic -l` is empty in the container | Same cause | Same fix. |
| FreeCAD or Blender MCP timeout | GUI closed or add-on not loaded | Reopen the GUI, check ports 9875 and 9876. |
| `memory` returns `503 AUTH_NOT_CONFIGURED` | Key empty or out of sync | Generate your key in `.env`, recreate the service, export the variable. |
| Trivy step red in CI | Read the message: `no space left on device` is not a vulnerability | Free runner disk space. |
| Standing test is slow (over 2 minutes) | Shared CPU, real-time factor below 1 | Normal: the test counts simulated time. |

## What "fully tested" means here

1. The stack starts, stays non-root and exposes no public port.
2. The robot stands for 10 simulated seconds in the delivered image, locally and in CI.
3. The five MCP servers answer real calls, not only `tools/list`.
4. The agent loop produces its artifacts end to end with guardrails active.
5. CI is green and the image scan leaves no fixable HIGH or CRITICAL vulnerability.
6. Every remaining gap is written in [verification-report.md](verification-report.md).
