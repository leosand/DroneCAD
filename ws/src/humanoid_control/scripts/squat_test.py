#!/usr/bin/env python3
"""DroneCAD — test de squat (consignes sinusoïdales) / squat test (sinusoidal commands).

EN: publishes sinusoidal knee/hip/ankle position commands on
    /joint_position_controller/commands and tracks /joint_states tracking error.
    Exit code 0 = tracking OK, 1 = tracking lost (max knee error > threshold).
FR : publie des consignes de position sinusoïdales (genou/hanche/cheville) sur
    /joint_position_controller/commands et suit l'erreur de suivi via /joint_states.
    Code de sortie 0 = suivi OK, 1 = suivi perdu (erreur max genou > seuil).
"""

from __future__ import annotations

import math
import sys

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
from std_msgs.msg import Float64MultiArray

# Ordre identique à humanoid_control/config/controllers.yaml / same order as the YAML
JOINTS: list[str] = [
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
assert len(JOINTS) == 28, "la liste de joints doit contenir 28 entrées"

KNEE_JOINTS = ("l_knee_pitch_joint", "r_knee_pitch_joint")
HIP_JOINTS = ("l_hip_pitch_joint", "r_hip_pitch_joint")
ANKLE_JOINTS = ("l_ankle_pitch_joint", "r_ankle_pitch_joint")

MAX_KNEE_ERROR_RAD = 0.25


class SquatTest(Node):
    def __init__(self, amplitude: float, period_s: float, duration_s: float, rate_hz: float) -> None:
        super().__init__("dronecad_squat_test")
        self.amplitude = amplitude
        self.period_s = period_s
        self.duration_s = duration_s
        self.rate_hz = rate_hz
        self.ticks = 0
        self.knee_target = 0.0
        self.max_knee_error = 0.0
        self.state: dict[str, float] = {}
        self.create_subscription(JointState, "/joint_states", self._on_state, 10)
        self.publisher = self.create_publisher(
            Float64MultiArray, "/joint_position_controller/commands", 10
        )
        self.timer = self.create_timer(1.0 / self.rate_hz, self._tick)

    def _on_state(self, msg: JointState) -> None:
        self.state = dict(zip(msg.name, msg.position))

    def _tick(self) -> None:
        self.ticks += 1
        t = self.ticks / self.rate_hz
        # Squat : flexion genou 0 → -amplitude → 0 / knee flexion cycle
        knee = -self.amplitude * (1.0 - math.cos(2.0 * math.pi * t / self.period_s)) / 2.0
        self.knee_target = knee
        hip = -knee / 2.0
        ankle = -knee / 2.0

        cmd = Float64MultiArray()
        values = []
        for name in JOINTS:
            if name in KNEE_JOINTS:
                values.append(knee)
            elif name in HIP_JOINTS:
                values.append(hip)
            elif name in ANKLE_JOINTS:
                values.append(ankle)
            else:
                values.append(0.0)
        cmd.data = values
        self.publisher.publish(cmd)

        if self.state:
            err = max(
                (abs(self.state.get(name, 0.0) - knee) for name in KNEE_JOINTS),
                default=0.0,
            )
            self.max_knee_error = max(self.max_knee_error, err)

    def done(self) -> bool:
        return self.ticks >= int(self.duration_s * self.rate_hz)


def main() -> int:
    amplitude = 0.35
    period_s = 4.0
    duration_s = 8.0
    rate_hz = 50.0

    rclpy.init()
    node = SquatTest(amplitude, period_s, duration_s, rate_hz)
    while rclpy.ok() and not node.done():
        rclpy.spin_once(node, timeout_sec=0.05)

    ok = node.max_knee_error < MAX_KNEE_ERROR_RAD
    node.get_logger().info(
        f"[squat_test] amplitude={amplitude} rad, durée={duration_s} s simulées — "
        f"erreur max genou={node.max_knee_error:.3f} rad (seuil {MAX_KNEE_ERROR_RAD}) → "
        f"{'OK' if ok else 'ÉCHEC'}"
    )
    node.destroy_node()
    rclpy.shutdown()
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
