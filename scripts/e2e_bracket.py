#!/usr/bin/env python3
"""DroneCAD — boucle agentique bout-en-bout (Phase 3 finale).

EN: full loop, guard-enforced (allowlist/timeout/journal/max 3 iterations):
    1. design   — FreeCAD MCP: parametric motor bracket (plate + hole) → pad → STEP + STL + screenshot
    2. model    — Blender MCP: STL import + wireframe enclosure → master .blend + GLB export
    3. simulate — headless Gazebo (container harness) + `ros2_topic_publish` squat command via the
                  ROS 2 MCP server + rosbag2 recording (/joint_states, /clock, /imu)
    4. analyze  — rosbags MCP: set_bag_path + bag_info + joint_states effort extraction
    5. iterate  — parametric adjustment + retry if any criterion fails (max 3)
FR : boucle complète, garde-fous actifs (allowlist/timeout/journal/max 3 itérations) — mêmes étapes.

Usage : python scripts/e2e_bracket.py [--knee -0.30] [--pub-duration 3.0] [--hold 10.0]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "agent"))

from agent_loop import (
    AgentLoop,
    IterationLimitReached,
    PhaseGuard,
    ToolCall,
    _mcp_command,
    load_allowlist,
)
from mcp_stdio import StdioMCPClient

ART = REPO / "artifacts"
JOURNAL = ART / "e2e_journal.jsonl"
CONTAINER = "dronecad-ros2-jazzy"
EFFORT_LIMIT_NM = 150.0
MIN_HEIGHT_M = 0.85

JOINTS = [
    "torso_yaw_joint", "torso_pitch_joint", "neck_yaw_joint", "neck_pitch_joint",
    "l_shoulder_pitch_joint", "l_shoulder_roll_joint", "l_shoulder_yaw_joint",
    "l_elbow_pitch_joint", "l_wrist_yaw_joint", "l_wrist_pitch_joint",
    "r_shoulder_pitch_joint", "r_shoulder_roll_joint", "r_shoulder_yaw_joint",
    "r_elbow_pitch_joint", "r_wrist_yaw_joint", "r_wrist_pitch_joint",
    "l_hip_yaw_joint", "l_hip_roll_joint", "l_hip_pitch_joint", "l_knee_pitch_joint",
    "l_ankle_pitch_joint", "l_ankle_roll_joint",
    "r_hip_yaw_joint", "r_hip_roll_joint", "r_hip_pitch_joint", "r_knee_pitch_joint",
    "r_ankle_pitch_joint", "r_ankle_roll_joint",
]


def text_of(raw: dict[str, Any] | None) -> str:
    """Concatène les blocs texte d'un résultat MCP / joins MCP text blocks."""
    if not raw:
        return ""
    parts = [item.get("text", "") for item in raw.get("content", []) if item.get("type") == "text"]
    if parts:
        return "\n".join(parts)
    if "structuredContent" in raw:
        return json.dumps(raw["structuredContent"], ensure_ascii=False)
    return json.dumps(raw, ensure_ascii=False)


def build_squat_command(knee: float) -> list[float]:
    """Consigne statique de squat (genou + compensations) / static squat command."""
    hip = -knee / 2.0
    ankle = -knee / 2.0
    values: list[float] = []
    for name in JOINTS:
        if name.endswith("knee_pitch_joint"):
            values.append(round(knee, 4))
        elif name.endswith("hip_pitch_joint"):
            values.append(round(hip, 4))
        elif name.endswith("ankle_pitch_joint"):
            values.append(round(ankle, 4))
        else:
            values.append(0.0)
    return values


def max_abs_effort(text: str) -> float | None:
    """Extrait le couple max (abs) des /joint_states / extracts max abs effort."""
    values: list[float] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "effort" and isinstance(value, list):
                    values.extend(abs(float(x)) for x in value if isinstance(x, (int, float)))
                else:
                    walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    try:
        walk(json.loads(text))
    except Exception:  # noqa: BLE001
        for match in re.finditer(r"effort['\"]?\s*[:=]\s*\[([^\]]+)\]", text):
            values.extend(
                abs(float(x))
                for x in re.findall(r"-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?", match.group(1))
            )
    return max(values) if values else None


class EndToEnd:
    def __init__(self, knee: float, pub_duration: float, hold: float) -> None:
        self.knee = knee
        self.pub_duration = pub_duration
        self.hold = hold
        self.run_id = uuid.uuid4().hex[:6]
        clients: dict[str, StdioMCPClient] = {}
        for server in ("freecad", "blender", "ros2", "rosbags"):
            command, env = _mcp_command(server)  # ${VAR} + résolution PATHEXT / expansion
            client = StdioMCPClient(command, name=server, env={**os.environ, **env})
            client.start(initialize_timeout_s=120.0)
            clients[server] = client
        self.clients = clients
        self.loop = AgentLoop(
            clients=clients,
            guard=PhaseGuard(load_allowlist()),
            journal_path=JOURNAL,
            max_iterations=3,
            call_timeout_s=150.0,
        )

    def close(self) -> None:
        for client in self.clients.values():
            client.stop()

    # ------------------------------------------------------------------ helpers
    def mcp(self, phase: str, server: str, tool: str, args: dict[str, Any], corr: str, iteration: int):
        return self.loop.submit(phase, ToolCall(server, tool, args), corr, iteration)

    def docker(self, script: str, timeout: float = 180.0) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["docker", "exec", CONTAINER, "bash", "-lc", script],
            capture_output=True, text=True, timeout=timeout, check=False,
        )

    # ------------------------------------------------------------------ phases
    def phase_design(self, it: int, corr: str) -> dict[str, Any]:
        """Conception paramétrique via `execute_python` (API FreeCAD directe).

        EN: the high-level sketch tools (`add_sketch_rectangle`, `pad_sketch`) return internal
        tracebacks on FreeCAD 1.1.3 (verified 2026-09-19); the bridge's `execute_python` tool is
        the documented escape hatch, so the bracket is built through the Part API (still fully
        parametric) — the decision is reported, not silent.
        FR : les outils haut niveau (`add_sketch_rectangle`, `pad_sketch`) produisent des
        tracebacks internes sur FreeCAD 1.1.3 (vérifié le 2026-09-19) ; l'outil `execute_python`
        du bridge est la trappe documentée — l'équerre est construite via l'API Part (toujours
        paramétrique) ; la décision est rapportée, pas silencieuse.
        """
        out: dict[str, Any] = {}
        plate_w, plate_h, plate_t, hole_r = 80.0, 100.0, 8.0, 6.0
        step_path = (ART / "motor_bracket.step").as_posix()
        stl_path = (ART / "motor_bracket.stl").as_posix()
        script = (
            "import FreeCAD as App, Part, Mesh\n"
            f'doc = App.newDocument("motor_bracket_v{it}")\n'
            f"plate = Part.makeBox({plate_w}, {plate_h}, {plate_t}, "
            f"App.Vector({-plate_w / 2}, {-plate_h / 2}, 0))\n"
            f"hole = Part.makeCylinder({hole_r}, {plate_t}, App.Vector(0, 0, 0))\n"
            "bracket = plate.cut(hole)\n"
            'obj = doc.addObject("Part::Feature", "bracket_body")\n'
            "obj.Shape = bracket\n"
            "doc.recompute()\n"
            "try:\n"
            f'    Part.export([obj], r"{step_path}")\n'
            "except Exception:\n"
            f'    obj.Shape.exportStep(r"{step_path}")\n'
            f'Mesh.export([obj], r"{stl_path}")\n'
            'print("BRACKET_OK", round(bracket.Volume, 1))\n'
        )

        def call(tool: str, args: dict[str, Any]) -> str:
            outcome = self.mcp("design", "freecad", tool, args, corr, it)
            if not outcome.ok:
                raise RuntimeError(f"design/{tool}: {outcome.error}")
            text = text_of(outcome.raw)
            if text.startswith("Error executing tool") or '"success":false' in text.replace(" ", ""):
                raise RuntimeError(f"design/{tool} — outil en erreur / tool error: {text[:300]}")
            return text

        text = call("execute_python", {"code": script, "timeout_ms": 60000})
        if "BRACKET_OK" not in text:
            raise RuntimeError(f"design/execute_python — sortie inattendue / unexpected: {text[:300]}")
        out["bracket"] = text.strip()[:200]
        # EN: evidence calls are tolerant — a buggy high-level tool must not block a valid part.
        # FR : les appels d'évidence sont tolérants — un outil haut niveau buggé ne doit pas
        #      bloquer une pièce valide.
        for tool, args in (
            ("list_objects", {}),
            ("get_screenshot", {"view_angle": "Isometric"}),
            ("save_document", {}),
        ):
            try:
                call(tool, args)
            except RuntimeError as exc:
                out.setdefault("warnings", []).append(str(exc)[:200])
        return out

    def phase_model(self, it: int, corr: str) -> dict[str, Any]:
        stl = (ART / "motor_bracket.stl").as_posix()
        blend = (ART / "motor_bracket_master.blend").as_posix()
        glb = (ART / "dronecad_enclosure.glb").as_posix()
        code = f'''
import bpy
from mathutils import Vector
existed = [o for o in bpy.data.objects if o.type == "MESH"]
for o in existed:
    bpy.data.objects.remove(o, do_unlink=True)
try:
    bpy.ops.wm.stl_import(filepath=r"{stl}", global_scale=0.001)
except Exception:
    bpy.ops.import_mesh.stl(filepath=r"{stl}", global_scale=0.001)
objs = [o for o in bpy.data.objects if o.type == "MESH"]
mins = Vector((1e9, 1e9, 1e9)); maxs = Vector((-1e9, -1e9, -1e9))
for o in objs:
    for corner in o.bound_box:
        world = o.matrix_world @ Vector(corner)
        for i in range(3):
            mins[i] = min(mins[i], world[i]); maxs[i] = max(maxs[i], world[i])
center = (mins + maxs) / 2.0
size = (maxs - mins) + Vector((0.03, 0.03, 0.03))
bpy.ops.mesh.primitive_cube_add(size=1.0, location=center)
box = bpy.context.active_object
box.name = "enclosure"
box.scale = (size.x / 2.0, size.y / 2.0, size.z / 2.0)
box.display_type = "WIRE"
bpy.ops.wm.save_as_mainfile(filepath=r"{blend}")
bpy.ops.export_scene.gltf(filepath=r"{glb}", export_format="GLB")
print("MODEL_OK", sorted(o.name for o in bpy.data.objects))
'''
        outcome = self.mcp("model", "blender", "execute_blender_code", {
            "user_prompt": "Importer le bracket FreeCAD, créer l'enveloppe, sauver le .blend maître et exporter GLB",
            "code": code,
        }, corr, it)
        if not outcome.ok:
            raise RuntimeError(f"model/execute_blender_code: {outcome.error}")
        return {"blender_text": text_of(outcome.raw)[:400], "outcome": outcome}

    def phase_simulate(self, it: int, corr: str) -> dict[str, Any]:
        out: dict[str, Any] = {}
        cleanup = (
            "kill -TERM -$(cat /tmp/e2e_bag.pid 2>/dev/null) 2>/dev/null; "
            "kill -TERM -$(cat /tmp/e2e_sim.pid 2>/dev/null) 2>/dev/null; sleep 2; "
            "kill -KILL -$(cat /tmp/e2e_sim.pid 2>/dev/null) 2>/dev/null; true"
        )
        self.docker(cleanup)
        self.docker("rm -rf /artifacts/e2e_bag")
        start = self.docker('''
source /opt/ros/jazzy/setup.bash && source /workspace/install/setup.bash
cd /workspace
setsid ros2 launch humanoid_gazebo sim.launch.py enable_camera:=false > /tmp/e2e_sim.log 2>&1 &
echo $! > /tmp/e2e_sim.pid
''')
        out["sim_start_rc"] = start.returncode
        deadline = time.time() + 90
        while time.time() < deadline:
            probe = self.docker(
                "source /opt/ros/jazzy/setup.bash && gz topic -l 2>/dev/null | grep -m1 '/model/humanoid/pose' || true"
            )
            if "/model/humanoid/pose" in probe.stdout:
                break
            time.sleep(3)
        else:
            raise RuntimeError("simulation: pose du modèle jamais publiée / model pose never published")
        time.sleep(6)  # contrôleurs actifs / controllers active

        bag = self.docker('''
source /opt/ros/jazzy/setup.bash && source /workspace/install/setup.bash
setsid ros2 bag record -o /artifacts/e2e_bag /joint_states /clock /imu > /tmp/e2e_bag.log 2>&1 &
echo $! > /tmp/e2e_bag.pid
''')
        out["bag_start_rc"] = bag.returncode
        time.sleep(3)

        publish = self.mcp("simulate", "ros2", "ros2_topic_publish", {
            "topic_name": "/joint_position_controller/commands",
            "message_type": "std_msgs/msg/Float64MultiArray",
            "data": {"data": build_squat_command(self.knee)},
            "frequency": 50.0,
            "duration": self.pub_duration,
        }, corr, it)
        if not publish.ok:
            raise RuntimeError(f"simulate/ros2_topic_publish: {publish.error}")
        out["publish"] = {"duration_ms": publish.duration_ms}

        time.sleep(self.hold)
        stop = self.docker('''
kill -INT $(cat /tmp/e2e_bag.pid) 2>/dev/null; sleep 3
ls /artifacts/e2e_bag 2>/dev/null | head -5
''')
        out["bag_files"] = stop.stdout.strip()

        pose = self.docker(
            "source /opt/ros/jazzy/setup.bash && timeout 10 gz topic -e -t /model/humanoid/pose -n 1 2>/dev/null"
        )
        z_match = re.search(r"position\s*\{[^}]*?z:\s*([-0-9.eE+]+)", pose.stdout, re.DOTALL)
        out["z"] = float(z_match.group(1)) if z_match else None

        self.docker(cleanup)
        out["bag_dir"] = str(ART / "e2e_bag")
        return out

    def phase_analyze(self, it: int, corr: str) -> dict[str, Any]:
        bag = (ART / "e2e_bag").as_posix()
        out: dict[str, Any] = {}

        def call(tool: str, args: dict[str, Any]) -> str:
            outcome = self.mcp("analyze", "rosbags", tool, args, corr, it)
            if not outcome.ok:
                raise RuntimeError(f"analyze/{tool}: {outcome.error}")
            return text_of(outcome.raw)

        call("set_bag_path", {"path": bag})
        info = call("bag_info", {"bag_path": bag})
        out["bag_info"] = info[:600]
        now = time.time()
        messages = call("get_messages_in_range", {
            "topic": "/joint_states", "start_time": now - 300, "end_time": now + 60,
            "max_messages": 40, "bag_path": bag,
        })
        (ART / "e2e_joint_states_sample.txt").write_text(messages[:400000], encoding="utf-8")
        out["effort_max"] = max_abs_effort(messages)
        out["messages_chars"] = len(messages)
        return out

    # ------------------------------------------------------------------ boucle
    def run(self) -> dict[str, Any]:
        history: list[dict[str, Any]] = []
        for iteration in range(1, self.loop.max_iterations + 1):
            corr = f"dronecad-e2e-{self.run_id}-it{iteration}"
            report: dict[str, Any] = {"iteration": iteration, "correlation_id": corr}
            try:
                report["design"] = {k: v for k, v in self.phase_design(iteration, corr).items() if k != "outcomes"}
                report["model"] = self.phase_model(iteration, corr).get("blender_text", "")[:200]
                report["simulate"] = self.phase_simulate(iteration, corr)
                report["analyze"] = self.phase_analyze(iteration, corr)
            except Exception as exc:  # noqa: BLE001 - l'échec est rapporté, pas masqué
                report["error"] = f"{type(exc).__name__}: {exc}"
                print(f"[e2e] itération {iteration} erreur: {report['error']}")
                history.append(report)
                self.knee *= 0.8
                continue

            files_ok = all(
                (ART / name).exists() and (ART / name).stat().st_size > 500
                for name in (
                    "motor_bracket.step", "motor_bracket.stl",
                    "motor_bracket_master.blend", "dronecad_enclosure.glb",
                )
            )
            sim = report["simulate"]
            analysis = report["analyze"]
            checks = {
                "files": files_ok,
                "bag_recorded": bool(sim.get("bag_files")),
                "no_fall": (sim.get("z") or 0) >= MIN_HEIGHT_M,
                "effort_within_limits": (
                    analysis.get("effort_max") is not None
                    and analysis["effort_max"] < EFFORT_LIMIT_NM
                ),
            }
            report["checks"] = checks
            report["success"] = all(checks.values())
            history.append(report)
            if report["success"]:
                return {"success": True, "history": history}
            print(json.dumps({
                "e2e_iteration_incomplete": iteration,
                "checks": checks,
                "z": sim.get("z"),
                "effort_max": analysis.get("effort_max"),
                "bag_files": bool(sim.get("bag_files")),
                "next_knee": round(self.knee * 0.8, 3),
            }, ensure_ascii=False))
            self.knee *= 0.8  # ajustement paramétrique / parametric adjustment
        raise IterationLimitReached(f"critères non satisfaits après {self.loop.max_iterations} itérations")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="DroneCAD — boucle agentique bout-en-bout")
    parser.add_argument("--knee", type=float, default=-0.30, help="flexion genou (rad, négatif)")
    parser.add_argument("--pub-duration", type=float, default=3.0, help="durée de publication MCP (s)")
    parser.add_argument("--hold", type=float, default=10.0, help="maintien après la consigne (s)")
    args = parser.parse_args(argv)

    ART.mkdir(exist_ok=True)
    e2e = EndToEnd(knee=args.knee, pub_duration=args.pub_duration, hold=args.hold)
    try:
        result = e2e.run()
    finally:
        e2e.close()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("E2E_OK" if result["success"] else "E2E_INCOMPLETE")
    return 0 if result["success"] else 1


if __name__ == "__main__":
    sys.exit(main())
