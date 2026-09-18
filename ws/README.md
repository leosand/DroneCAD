# ws/ — Espace de travail colcon / Colcon workspace

> EN: Phase 2 creates the three ROS 2 packages here. / FR-CA : la Phase 2 crée ici les trois paquets ROS 2.

| Package | Rôle / role | État / state |
|---|---|---|
| `ws/src/humanoid_description` | URDF/Xacro humanoïde 24–32 DoF : torso, tête (caméra RGB-D + IMU), bras 6 DoF ×2, jambes 6 DoF ×2 ; masses/inerties valides ; transmissions `ros2_control` ; export reproductible depuis un `.blend` maître | ⏳ Phase 2 |
| `ws/src/humanoid_gazebo` | Mondes Gazebo Harmonic (sol plat + obstacles), launch files, pont `ros_gz_bridge` (`/clock`, `/joint_states`, `/camera`, `/imu`) | ⏳ Phase 2 |
| `ws/src/humanoid_control` | Contrôleurs `ros2_control` (position + effort), YAML, test de squat (consignes sinusoïdales) | ⏳ Phase 2 |

- Build (conteneur) : `docker compose up -d ros2-jazzy && docker compose exec ros2-jazzy bash -lc "cd /workspace && colcon build"`.
- Tests prévus : pytest de validation URDF (`check_urdf`, inerties > 0, aucun lien orphelin) + test d'intégration Gazebo sans interface (robot debout ≥ 10 s simulées). Suivi de l'état : `REPORT.md`.
