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
      ros-jazzy-gz-ros2-control \
      ros-jazzy-ros2-control \
      ros-jazzy-ros2-controllers \
      ros-jazzy-moveit \
      ros-jazzy-xacro \
      ros-jazzy-robot-state-publisher \
      ros-jazzy-joint-state-publisher \
      ros-jazzy-joint-state-publisher-gui \
      liburdfdom-tools \
      python3-pip python3-venv git curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# ---------- Stage 2 : mcp (vendoring isolé — outillage hors image finale) ----------
FROM base AS mcp
# EN: pinned audited tag 2606 / FR : tag 2606 audité, épinglé
# EN: sync with the SYSTEM python — uv would otherwise download a managed interpreter into
#     /root or $HOME, unavailable to the non-root runtime user and incompatible with rclpy
#     (3.12). The final assertion makes a silent regression fail the build (verified 2026-09-18).
# FR : synchroniser avec le python SYSTÈME — sinon uv télécharge un interpréteur géré sous
#     /root ou $HOME, inaccessible au non-root et incompatible avec rclpy (3.12). L'assertion
#     finale fait échouer le build en cas de régression silencieuse (vérifié le 2026-09-18).
RUN git clone --depth 1 --branch 2606 https://github.com/wise-vision/ros2_mcp /opt/ros2-mcp \
 && curl -LsSf https://astral.sh/uv/install.sh | sh \
 && cd /opt/ros2-mcp \
 && rm -f .python-version \
 && UV_PYTHON_DOWNLOADS=never /root/.local/bin/uv venv --python /usr/bin/python3.12 --no-managed-python \
 && UV_PYTHON_DOWNLOADS=never /root/.local/bin/uv sync --python /usr/bin/python3.12 --no-managed-python \
 && /opt/ros2-mcp/.venv/bin/python -c "import sys; assert sys.version_info[:2] == (3, 12), sys.version" \
 && UV_PYTHON_DOWNLOADS=never /root/.local/bin/uv pip install --python /opt/ros2-mcp/.venv/bin/python \
      --upgrade \
      "pillow>=12.3.0" \
      "cryptography>=50.0.0" \
      "python-multipart>=0.0.30"

# EN: the last step is a targeted security bump — Trivy HIGH/CRITICAL *fixable* findings in the
#     vendored venv (2026-09-19): pillow (CVE-2026-42311 arbitrary code exec, …), cryptography
#     (CVE-2026-69247 oracle), python-multipart (CVE-2026-24486 path traversal).
# FR : la dernière étape est un correctif de sécurité ciblé — constats Trivy HIGH/CRITICAL
#     corrigeables dans le venv vendoré (2026-09-19) : pillow (exécution de code, …), cryptography
#     (oracle), python-multipart (traversée de chemin).

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

# EN: Fast DDS "localhost" profile (explicit loopback peers, no multicast). Shipped but only
#     activated where the environment lacks multicast (CI runners) through
#     FASTRTPS_DEFAULT_PROFILES_FILE — the workstation keeps the default discovery.
# FR : profil Fast DDS « localhost » (pairs loopback explicites, sans multicast). Embarqué mais
#     activé seulement là où le multicast manque (runners CI) via
#     FASTRTPS_DEFAULT_PROFILES_FILE — la station conserve la découverte par défaut.
COPY fastdds-localhost.xml /opt/dronecad/fastdds-localhost.xml

ENV HOME=/home/ubuntu
RUN chown -R 1000:1000 /workspace /artifacts /opt/ros2-mcp

USER 1000:1000
WORKDIR /workspace

# EN: stay alive; shells/commands via `docker exec` (ros2 MCP entry, tests)
# FR : reste actif ; shells/commandes via `docker exec` (entrée MCP ros2, tests)
CMD ["bash", "-lc", "source /opt/ros/jazzy/setup.bash && sleep infinity"]
