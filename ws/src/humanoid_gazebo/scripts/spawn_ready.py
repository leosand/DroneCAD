#!/usr/bin/env python3
"""DroneCAD — spawn du robot une fois le serveur Gazebo réellement prêt.

EN: `ros_gz_sim create` exposes no "wait until the world exists" flag. The launch used a fixed
    2 s timer, which is a race: on a slow CI runner Gazebo was still loading, the spawn failed
    silently and the robot never appeared for the whole 90 s wait (CI run 35412876213,
    2026-09-19). This wrapper blocks until `/world/<world>/create` is advertised *and*
    `/robot_description` has a publisher, then spawns with retries.
FR : `ros_gz_sim create` n'expose aucune option « attendre l'existence du monde ». Le launch
    utilisait une minuterie fixe de 2 s, ce qui est une course : sur un runner CI lent, Gazebo
    chargeait encore, le spawn échouait silencieusement et le robot n'apparaissait jamais
    pendant les 90 s d'attente (run CI 35412876213, 2026-09-19). Ce wrapper bloque jusqu'à
    l'annonce de `/world/<world>/create` *et* la présence d'un éditeur sur
    `/robot_description`, puis spawne avec réessais.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time

SERVICE_TIMEOUT_S = 180.0
TOPIC_TIMEOUT_S = 60.0
SPAWN_RETRIES = 3


def _world_service_up(world: str) -> bool:
    """Le service de création du monde est-il annoncé ? / is the world create service up?"""
    try:
        out = subprocess.run(
            ["gz", "service", "-l"], capture_output=True, text=True, timeout=15, check=False
        ).stdout
    except (OSError, subprocess.TimeoutExpired):
        return False
    return f"/world/{world}/create" in out


def _topic_published(topic: str) -> bool:
    """Un éditeur publie-t-il ce topic ? / does any publisher exist on that topic?"""
    try:
        out = subprocess.run(
            ["ros2", "topic", "info", topic, "--verbose"],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        ).stdout
    except (OSError, subprocess.TimeoutExpired):
        return False
    return "Publisher count: 0" not in out and "Publisher count" in out


def _wait_for(predicate, timeout_s: float, label: str) -> bool:
    """Attente active bornée / bounded polling wait."""
    deadline = time.monotonic() + timeout_s
    start = time.monotonic()
    while time.monotonic() < deadline:
        if predicate():
            print(f"[spawn_ready] {label} prêt après {time.monotonic() - start:.1f} s", flush=True)
            return True
        time.sleep(1.0)
    print(f"[spawn_ready] {label} absent après {timeout_s:.0f} s", flush=True)
    return False


def main(argv: list[str] | None = None) -> int:
    # EN: parse_known_args — the launch may append `--ros-args -p use_sim_time:=true`
    # FR : parse_known_args — le launch peut ajouter `--ros-args -p use_sim_time:=true`
    parser = argparse.ArgumentParser(description="Spawn the humanoid once Gazebo is ready")
    parser.add_argument("--world", default="flat_ground")
    parser.add_argument("--topic", default="/robot_description")
    parser.add_argument("--name", default="humanoid")
    parser.add_argument("--z", default="1.08")
    args, _unknown = parser.parse_known_args(argv)

    if not _wait_for(lambda: _world_service_up(args.world), SERVICE_TIMEOUT_S, "serveur Gazebo"):
        return 1
    if not _wait_for(lambda: _topic_published(args.topic), TOPIC_TIMEOUT_S, args.topic):
        return 1

    cmd = [
        "ros2", "run", "ros_gz_sim", "create",
        "-world", args.world,
        "-topic", args.topic,
        "-name", args.name,
        "-z", args.z,
    ]
    for attempt in range(1, SPAWN_RETRIES + 1):
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if proc.returncode == 0:
            print(f"[spawn_ready] spawn OK (essai {attempt}/{SPAWN_RETRIES})", flush=True)
            return 0
        detail = (proc.stderr or proc.stdout or "").strip().replace("\n", " ")[:300]
        print(f"[spawn_ready] essai {attempt}/{SPAWN_RETRIES} échoué : {detail}", flush=True)
        time.sleep(5.0)
    print("[spawn_ready] spawn impossible après réessais / spawn failed after retries", flush=True)
    return 1


if __name__ == "__main__":
    sys.exit(main())
