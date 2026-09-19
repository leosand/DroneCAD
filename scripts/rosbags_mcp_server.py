#!/usr/bin/env python3
"""DroneCAD — wrapper de compatibilité pour vendor/mcp-rosbags (rosbags moderne).

EN: the vendored mcp-rosbags (upstream stale, last commit 2025-09) imports the pre-0.10
    rosbags API — ``from rosbags.serde import deserialize_cdr`` / ``serialize_cdr`` — while
    reading ROS 2 Jazzy bags REQUIRES modern rosbags (rosbag2 metadata v9). This wrapper
    restores the legacy functions on top of the modern typestore (ROS2_JAZZY) before loading
    the server, without touching the pristine submodule (fork-in-place pattern).
FR : le mcp-rosbags vendoré (amont stale) importe l'API rosbags d'avant 0.10 — ``deserialize_cdr``
    et ``serialize_cdr`` depuis ``rosbags.serde`` — alors que lire les bags ROS 2 Jazzy EXIGE
    rosbags moderne (métadonnées rosbag2 v9). Ce wrapper rétablit les fonctions historiques
    au-dessus du typestore moderne (ROS2_JAZZY) avant de charger le serveur, sans toucher au
    sous-module vierge (patron fork-in-place).

Constats vérifiés le 2026-09-19 :
  - bag v9 : `rosbags<0.10` → « Rosbag2 version 9 not supported » ; rosbags moderne le lit.
  - moderne : `Stores.ROS2_JAZZY` + `typestore.{de,}serialize_cdr` disponibles ; imports du
    vendor limités à `Reader`/`Writer` (rosbags.rosbag2) + les deux fonctions ci-dessus.
"""

from __future__ import annotations

import pathlib
import runpy
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
VENDOR_SRC = REPO / "vendor" / "mcp-rosbags" / "src"

if not VENDOR_SRC.is_dir():
    sys.exit(
        "vendor/mcp-rosbags absent — initialiser le sous-module : "
        "git submodule update --init vendor/mcp-rosbags"
    )

# 1) Shim de l'API historique AVANT l'import du serveur vendoré.
import rosbags.serde as _serde  # noqa: E402

if not hasattr(_serde, "deserialize_cdr") or not hasattr(_serde, "serialize_cdr"):
    from rosbags.typesys import Stores, get_typestore  # noqa: E402

    _store = get_typestore(Stores.ROS2_JAZZY)

    if not hasattr(_serde, "deserialize_cdr"):

        def deserialize_cdr(rawdata: bytes, msgtype: str, *_: object, **__: object) -> object:
            """Ancienne API → typestore moderne / legacy API → modern typestore."""
            return _store.deserialize_cdr(rawdata, msgtype)

        _serde.deserialize_cdr = deserialize_cdr  # type: ignore[attr-defined]

    if not hasattr(_serde, "serialize_cdr"):

        def serialize_cdr(message: object, msgtype: str, *_: object, **__: object) -> bytes:
            """Ancienne API → typestore moderne / legacy API → modern typestore."""
            return _store.serialize_cdr(message, msgtype)

        _serde.serialize_cdr = serialize_cdr  # type: ignore[attr-defined]

# 2) Lancement du serveur vendoré tel quel (son __main__ fait asyncio.run(main())).
sys.path.insert(0, str(VENDOR_SRC))
runpy.run_path(str(VENDOR_SRC / "server.py"), run_name="__main__")
