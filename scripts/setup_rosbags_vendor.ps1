# ============================================================
# setup_rosbags_vendor.ps1 — Recrée le venv du sous-module mcp-rosbags
# EN: the vendored mcp-rosbags server needs a dedicated venv; `mcp` must be pinned <2
#     (mcp 2.x removed `Server.list_tools()`, used by the 2025-era server) and modern
#     `rosbags` is required to read ROS 2 Jazzy bags (metadata v9). The wrapper
#     scripts/rosbags_mcp_server.py restores the legacy rosbags.serde API on top.
# FR : le serveur mcp-rosbags vendoré a besoin d'un venv dédié ; `mcp` doit être pinné <2
#     (mcp 2.x a retiré `Server.list_tools()`, utilisé par le serveur de 2025) et `rosbags`
#     moderne est requis pour lire les bags ROS 2 Jazzy (métadonnées v9). Le wrapper
#     scripts/rosbags_mcp_server.py rétablit l'API historique rosbags.serde par-dessus.
#
# Usage (depuis la racine du repo) :
#   powershell -NoProfile -File scripts\setup_rosbags_vendor.ps1
# ============================================================
$ErrorActionPreference = 'Stop'
$Repo = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$Ven = Join-Path $Repo 'vendor\mcp-rosbags\.venv'
$Requirements = Join-Path $Repo 'vendor\mcp-rosbags\requirements.txt'

if (-not (Test-Path $Requirements)) {
    throw "Sous-module absent — exécuter : git submodule update --init vendor/mcp-rosbags"
}

Write-Host "Création du venv : $Ven"
python -m venv $Ven
& "$Ven\Scripts\python.exe" -m pip install --quiet --upgrade pip
& "$Ven\Scripts\python.exe" -m pip install --quiet -r $Requirements
Write-Host "Pin mcp<2 (compat serveur vendoré 2025)"
& "$Ven\Scripts\python.exe" -m pip install --quiet "mcp<2"
& "$Ven\Scripts\python.exe" -c "import rosbags, mcp, yaml; print('venv rosbags OK — mcp', mcp.__version__ if hasattr(mcp,'__version__') else 'ok')"
Write-Host "Terminé. .mcp.json pointe sur $Ven\Scripts\python.exe"
