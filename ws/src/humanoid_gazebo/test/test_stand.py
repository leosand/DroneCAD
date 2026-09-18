"""DroneCAD — test d'intégration : le robot reste debout ≥ 10 s simulées (Gazebo Harmonic).

EN: launches the headless simulation, samples the model pose via `gz topic` and the simulated
    time via `/clock`, and asserts the base stays upright for at least 10 simulated seconds.
    This is the founding brief's Phase 2 acceptance gate.
FR : lance la simulation sans interface, échantillonne la pose du modèle via `gz topic` et le
    temps simulé via `/clock`, puis vérifie que le robot reste debout ≥ 10 s simulées.
    Porte d'acceptation Phase 2 du brief fondateur.
"""

from __future__ import annotations

import math
import os
import re
import shutil
import signal
import subprocess
import time

import pytest

POSE_TOPIC = "/model/humanoid/pose"
MIN_HEIGHT_M = 0.85          # base_link z nominal ≈ 1.06 m ; chute → ≈ 0.15 m
MAX_TILT_RAD = 0.35
REQUIRED_SIM_SECONDS = 10.0

pytestmark = pytest.mark.skipif(
    shutil.which("gz") is None or os.environ.get("DRONECAD_SKIP_SIM") == "1",
    reason="gz introuvable ou simulation désactivée / gz missing or simulation disabled",
)


def _sample_pose(timeout_s: float = 6.0) -> tuple[float, float, float] | None:
    """Retourne (z, roll, pitch) du modèle ou None / model (z, roll, pitch) or None."""
    try:
        out = subprocess.run(
            ["gz", "topic", "-e", "-t", POSE_TOPIC, "-n", "1"],
            capture_output=True,
            text=True,
            timeout=timeout_s,
        ).stdout
    except subprocess.TimeoutExpired:
        return None
    z_m = re.search(r"position\s*\{[^}]*?z:\s*([-0-9.eE+]+)", out, re.S)
    ori = re.search(
        r"orientation\s*\{[^}]*?x:\s*([-0-9.eE+]+)[^}]*?y:\s*([-0-9.eE+]+)"
        r"[^}]*?z:\s*([-0-9.eE+]+)[^}]*?w:\s*([-0-9.eE+]+)",
        out,
        re.S,
    )
    if not z_m or not ori:
        return None
    z = float(z_m.group(1))
    qx, qy, qz, qw = (float(g) for g in ori.groups())
    roll = math.atan2(2.0 * (qw * qx + qy * qz), 1.0 - 2.0 * (qx * qx + qy * qy))
    pitch = math.asin(max(-1.0, min(1.0, 2.0 * (qw * qy - qz * qx))))
    return z, roll, pitch


def _sim_seconds(timeout_s: float = 15.0) -> float | None:
    """Temps simulé courant via /clock / current simulated time via /clock."""
    try:
        out = subprocess.run(
            ["ros2", "topic", "echo", "--once", "/clock"],
            capture_output=True,
            text=True,
            timeout=timeout_s,
        ).stdout
    except subprocess.TimeoutExpired:
        return None
    sec = re.search(r"sec:\s*(\d+)", out)
    nsec = re.search(r"nanosec:\s*(\d+)", out)
    if not sec:
        return None
    return int(sec.group(1)) + (int(nsec.group(1)) / 1e9 if nsec else 0.0)


def test_robot_stands_10_simulated_seconds() -> None:
    launch = subprocess.Popen(
        [
            "ros2", "launch", "humanoid_gazebo", "sim.launch.py",
            "enable_camera:=false", "world_file:=flat_ground.sdf",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
        preexec_fn=os.setsid,
    )
    try:
        # EN: wait until the robot is spawned (pose available, z plausible)
        # FR : attendre que le robot soit apparu (pose disponible, z plausible)
        deadline = time.time() + 90.0
        first: tuple[float, float, float] | None = None
        while time.time() < deadline:
            sample = _sample_pose()
            if sample is not None and sample[0] > 0.5:
                first = sample
                break
            time.sleep(2.0)
        assert first is not None, "le robot n'est jamais apparu / robot never spawned"

        # EN: wait for ≥ 10 simulated seconds (not wall-clock: RTF may be < 1)
        # FR : attendre ≥ 10 s simulées (pas l'horloge murale : la RTF peut être < 1)
        t_start = _sim_seconds()
        assert t_start is not None, "pas de /clock — simulation non démarrée / no /clock"
        hard_deadline = time.time() + 180.0
        while time.time() < hard_deadline:
            now = _sim_seconds()
            if now is not None and (now - t_start) >= REQUIRED_SIM_SECONDS:
                break
            time.sleep(2.0)
        else:
            pytest.fail("temps simulé insuffisant / not enough simulated time elapsed")

        final = _sample_pose()
        assert final is not None, "pose finale indisponible / final pose unavailable"
        z, roll, pitch = final
        assert z > MIN_HEIGHT_M, f"chute détectée / robot fell: z={z:.3f} m"
        assert abs(roll) < MAX_TILT_RAD, f"roulis excessif / excessive roll: {roll:.3f} rad"
        assert abs(pitch) < MAX_TILT_RAD, f"tangage excessif / excessive pitch: {pitch:.3f} rad"
        print(
            f"[test_stand] OK — z={z:.3f} m, roll={roll:.3f}, pitch={pitch:.3f} "
            f"après {REQUIRED_SIM_SECONDS:.0f} s simulées"
        )
    finally:
        # EN: clean shutdown of the whole launch process group / FR : arrêt propre du groupe
        try:
            os.killpg(os.getpgid(launch.pid), signal.SIGINT)
            launch.wait(timeout=20)
        except (subprocess.TimeoutExpired, ProcessLookupError):
            try:
                os.killpg(os.getpgid(launch.pid), signal.SIGKILL)
            except ProcessLookupError:
                pass
