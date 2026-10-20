# The IFS slots in Moonraker's database, namespace "lane_data", for slicers
#
# OrcaSlicer's Moonraker printer agent (nightlies after 2.4.2, Preferences >
# Developer > "Use printer agents instead of print hosts") reads
# /server/database/item?namespace=lane_data to fill its filament list with
# what is loaded, the same data AFC writes. One record per IFS slot:
#   lane1..lane4: {"lane": "0".."3"  (the slicer tool: slot 1 = T0, as
#                                     IFS_MAP_TOOL's default map)
#                  "material": "PLA" ("" = no filament or no type set)
#                  "color": "#RRGGBB", "nozzle_temp": 220, "bed_temp": 0,
#                  "name", "vendor", "spool_id", "scan_time" (AFC's
#                  remaining fields, empty)}
# Kept up to date from Klipper's ifs_materials (IFS_SET_MATERIAL, the touch
# screen) and ifs.loaded_channels (a slot without filament is empty).
#
# [kiln_lanes]
#
# This file may be distributed under the terms of the GNU GPLv3 license.

from __future__ import annotations
import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from ..confighelper import ConfigHelper

NAMESPACE = "lane_data"
SLOTS = (1, 2, 3, 4)


def build_lanes(materials: Dict[str, Any],
                ifs: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """lane_data records from printer.ifs_materials and printer.ifs."""
    slots = materials.get("slots") or {}
    present: Optional[List[int]] = None
    if ifs.get("connected") and ifs.get("loaded_channels") is not None:
        present = list(ifs["loaded_channels"])
    lanes = {}
    for s in SLOTS:
        m = slots.get(str(s)) or {}
        mtype = m.get("type") or ""
        if present is not None and s not in present:
            mtype = ""
        temp = m.get("temp") if mtype else None
        lanes[f"lane{s}"] = {
            "lane": str(s - 1),
            "material": mtype,
            "color": (m.get("color") or "") if mtype else "",
            "nozzle_temp": int(round(temp)) if temp else 0,
            "bed_temp": 0,
            "name": "",
            "vendor": "",
            "spool_id": None,
            "scan_time": "",
        }
    return lanes


class KilnLanes:
    def __init__(self, config: ConfigHelper) -> None:
        self.server = config.get_server()
        self.db = self.server.load_component(config, "database")
        self.materials: Dict[str, Any] = {}
        self.ifs: Dict[str, Any] = {}
        self.written: Optional[Dict[str, Any]] = None
        self.server.register_event_handler(
            "server:klippy_ready", self._on_ready)

    async def _on_ready(self) -> None:
        kapis = self.server.lookup_component("klippy_apis")
        objs = {"ifs_materials": None,
                "ifs": ["connected", "loaded_channels"]}
        try:
            status = await kapis.subscribe_objects(objs, self._on_status)
        except self.server.error as e:
            logging.info(f"kiln_lanes: no IFS in Klipper ({e})")
            return
        if "ifs_materials" not in status:
            logging.info("kiln_lanes: no [ifs] in Klipper, lane_data unused")
            return
        self.materials = status.get("ifs_materials") or {}
        self.ifs = status.get("ifs") or {}
        await self._write()

    async def _on_status(self, status: Dict[str, Any],
                         eventtime: float) -> None:
        changed = False
        if "ifs_materials" in status:
            self.materials.update(status["ifs_materials"])
            changed = True
        if "ifs" in status:
            self.ifs.update(status["ifs"])
            changed = True
        if changed and self.materials:
            await self._write()

    async def _write(self) -> None:
        lanes = build_lanes(self.materials, self.ifs)
        if lanes == self.written:
            return
        await self.db.insert_batch(NAMESPACE, lanes)
        self.written = lanes
        logging.debug(f"kiln_lanes: {lanes}")


def load_component(config: ConfigHelper) -> KilnLanes:
    return KilnLanes(config)
