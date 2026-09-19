"""DroneCAD — validation structurelle de l'URDF humanoïde / humanoid URDF structural validation.

EN: processes the xacro, then checks tree integrity (single root, references), masses,
    inertias (positive + triangle inequality), joint limits, DoF count and ros2_control
    interfaces. `check_urdf` is run too when the binary is available.
FR : traite le xacro, puis vérifie l'intégrité de l'arbre (racine unique, références), les masses,
    les inerties (positives + inégalité triangulaire), les limites articulaires, le nombre de DoF
    et les interfaces ros2_control. `check_urdf` est aussi exécuté quand le binaire est présent.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

URDF_DIR = Path(__file__).resolve().parent.parent / "urdf"
XACRO_FILE = URDF_DIR / "humanoid.urdf.xacro"

REVOLUTE_TYPES = {"revolute", "prismatic", "continuous"}


def _xacro_command() -> list[str] | None:
    """Binaire `xacro` (PATH), sinon homologue du venv à côté de Python.

    EN: PATH binary first, then the venv sibling of sys.executable (CI runs pytest from a venv
    whose bin/ is not on PATH). / FR : binaire du PATH d'abord, puis l'homologue du venv à côté
    de sys.executable (la CI lance pytest depuis un venv dont bin/ n'est pas dans le PATH).
    """
    binary = shutil.which("xacro")
    if binary:
        return [binary]
    sibling = Path(sys.executable).parent / ("xacro.exe" if os.name == "nt" else "xacro")
    if sibling.exists():
        return [str(sibling)]
    return None


@pytest.fixture(scope="module")
def robot() -> ET.Element:
    command = _xacro_command()
    if command is None:
        pytest.skip("xacro introuvable / xacro not found")
    result = subprocess.run(
        command + [str(XACRO_FILE)], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, f"xacro a échoué / failed:\n{result.stderr}"
    return ET.fromstring(result.stdout)


@pytest.fixture(scope="module")
def urdf_text(robot: ET.Element) -> str:
    return ET.tostring(robot, encoding="unicode")


def _links(robot: ET.Element) -> dict[str, ET.Element]:
    return {link.get("name"): link for link in robot.findall("link")}


def _joints(robot: ET.Element) -> list[ET.Element]:
    return robot.findall("joint")


def test_dof_count_in_24_32(robot: ET.Element) -> None:
    dof = [j for j in _joints(robot) if j.get("type") in REVOLUTE_TYPES]
    assert 24 <= len(dof) <= 32, f"DoF hors plage brief (24-32) : {len(dof)}"


def test_unique_link_names(robot: ET.Element) -> None:
    names = [link.get("name") for link in robot.findall("link")]
    assert len(names) == len(set(names)), "noms de liens dupliqués / duplicate link names"


def test_single_root_base_link(robot: ET.Element) -> None:
    links = set(_links(robot))
    children = {j.find("child").get("link") for j in _joints(robot)}
    roots = links - children
    assert roots == {"base_link"}, f"racine(s) inattendue(s) / unexpected root(s): {roots}"


def test_joint_references_exist(robot: ET.Element) -> None:
    links = set(_links(robot))
    for joint in _joints(robot):
        parent = joint.find("parent").get("link")
        child = joint.find("child").get("link")
        assert parent in links, f"{joint.get('name')}: parent inconnu / unknown parent {parent}"
        assert child in links, f"{joint.get('name')}: child inconnu / unknown child {child}"


def test_no_orphan_links(robot: ET.Element) -> None:
    links = set(_links(robot))
    referenced = {j.find("parent").get("link") for j in _joints(robot)}
    referenced |= {j.find("child").get("link") for j in _joints(robot)}
    orphans = links - referenced
    assert not orphans, f"liens orphelins / orphan links: {orphans}"


def test_masses_positive(robot: ET.Element) -> None:
    for link in robot.findall("link"):
        mass = link.find("inertial/mass")
        assert mass is not None, f"{link.get('name')}: masse absente / missing mass"
        assert float(mass.get("value")) > 0, f"{link.get('name')}: masse <= 0"


def test_inertias_positive_definite(robot: ET.Element) -> None:
    for link in robot.findall("link"):
        inertia = link.find("inertial/inertia")
        assert inertia is not None, f"{link.get('name')}: inertie absente / missing inertia"
        ixx, iyy, izz = (float(inertia.get(k)) for k in ("ixx", "iyy", "izz"))
        assert ixx > 0 and iyy > 0 and izz > 0, f"{link.get('name')}: diagonale non positive"
        # Inégalité triangulaire des moments principaux / triangle inequality
        assert ixx + iyy >= izz, f"{link.get('name')}: ixx+iyy < izz"
        assert iyy + izz >= ixx, f"{link.get('name')}: iyy+izz < ixx"
        assert ixx + izz >= iyy, f"{link.get('name')}: ixx+izz < iyy"


def test_joint_limits_valid(robot: ET.Element) -> None:
    for joint in _joints(robot):
        if joint.get("type") not in REVOLUTE_TYPES:
            continue
        limit = joint.find("limit")
        assert limit is not None, f"{joint.get('name')}: limite absente / missing limit"
        lower, upper = float(limit.get("lower")), float(limit.get("upper"))
        assert lower <= upper, f"{joint.get('name')}: lower > upper"
        assert float(limit.get("effort")) > 0 and float(limit.get("velocity")) > 0


def test_axes_are_unit(robot: ET.Element) -> None:
    for joint in _joints(robot):
        axis = joint.find("axis")
        if axis is None:
            continue
        x, y, z = (float(v) for v in axis.get("xyz").split())
        norm = (x * x + y * y + z * z) ** 0.5
        assert abs(norm - 1.0) < 1e-6, f"{joint.get('name')}: axe non unitaire ({norm})"


def test_ros2_control_interfaces(robot: ET.Element) -> None:
    rc = robot.find("ros2_control")
    assert rc is not None, "bloc ros2_control absent / missing"
    joints = rc.findall("joint")
    dof = [j for j in _joints(robot) if j.get("type") in REVOLUTE_TYPES]
    assert len(joints) == len(dof), (
        f"ros2_control déclare {len(joints)} joints, l'URDF en a {len(dof)}"
    )
    for joint in joints:
        commands = {c.get("name") for c in joint.findall("command_interface")}
        states = {s.get("name") for s in joint.findall("state_interface")}
        assert "position" in commands, f"{joint.get('name')}: interface position manquante"
        assert {"position", "velocity", "effort"} <= states


def test_check_urdf_binary(robot: ET.Element, tmp_path: Path, urdf_text: str) -> None:
    check = shutil.which("check_urdf")
    if check is None:
        pytest.skip("check_urdf introuvable / not found (urdfdom)")
    urdf_file = tmp_path / "humanoid.urdf"
    urdf_file.write_text(urdf_text, encoding="utf-8")
    result = subprocess.run([check, str(urdf_file)], capture_output=True, text=True, check=False)
    assert result.returncode == 0, f"check_urdf a échoué / failed:\n{result.stdout}\n{result.stderr}"
