# syntax=docker/dockerfile:1
# ============================================================
# DroneCAD — image ros2-jazzy : ROS 2 Jazzy + Gazebo Harmonic + ros2_control + MoveIt 2
# EN: multi-stage build. `base` = OS/ROS/Gazebo layers; `mcp` = vendored ros2_mcp (tooling
#     isolated from the shipped image); `runtime` = shipped image, non-root (uid 1000).
# FR : construction multi-étapes. `base` = couches OS/ROS/Gazebo ; `mcp` = ros2_mcp vendoré
#     (outillage isolé de l'image livrée) ; `runtime` = image livrée, non-root (uid 1000).
# Sources auditées (2026-09-18) : gazebosim/ros_gz, ros-controls/ros2_control, moveit/moveit2,
#     wise-vision/ros2_mcp (tag 2606) — voir README.md § Reference repositories audited.
# ============================================================

# ---------- Stage 1 : base ----------
FROM ros:jazzy AS base
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
      ros-jazzy-ros-gz \
      ros-jazzy-ros2-control \
      ros-jazzy-ros2-controllers \
      ros-jazzy-moveit \
      ros-jazzy-xacro \
      ros-jazzy-robot-state-publisher \
      ros-jazzy-joint-state-publisher \
      ros-jazzy-joint-state-publisher-gui \
      python3-pip python3-venv git curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# ---------- Stage 2 : mcp (vendoring isolé — outillage hors image finale) ----------
FROM base AS mcp
# EN: pinned audited tag 2606 / FR : tag 2606 audité, épinglé
RUN git clone --depth 1 --branch 2606 https://github.com/wise-vision/ros2_mcp /opt/ros2-mcp \
 && curl -LsSf https://astral.sh/uv/install.sh | sh \
 && /root/.local/bin/uv sync --directory /opt/ros2-mcp

# ---------- Stage 3 : runtime (image livrée) ----------
FROM base AS runtime
LABEL org.opencontainers.image.title="DroneCAD ros2-jazzy" \
      org.opencontainers.image.source="https://github.com/leosand/DroneCAD"

# EN: the official ROS image already provides uid 1000 (`ubuntu`) — reuse it; adding a second
#     `useradd -u 1000` fails (verified build error, 2026-09-18).
# FR : l'image ROS officielle fournit déjà l'uid 1000 (`ubuntu`) — réutilisé ; un second
#     `useradd -u 1000` échoue (erreur de build vérifiée le 2026-09-18).
RUN mkdir -p /workspace /artifacts

COPY --from=mcp /opt/ros2-mcp /opt/ros2-mcp
COPY --from=mcp /root/.local/bin/uv /usr/local/bin/uv

ENV HOME=/home/ubuntu
RUN chown -R 1000:1000 /workspace /artifacts /opt/ros2-mcp

USER 1000:1000
WORKDIR /workspace

# EN: stay alive; shells/commands via `docker exec` (ros2 MCP entry, tests)
# FR : reste actif ; shells/commandes via `docker exec` (entrée MCP ros2, tests)
CMD ["bash", "-lc", "source /opt/ros/jazzy/setup.bash && sleep infinity"]
