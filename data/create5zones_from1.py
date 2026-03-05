import copy
import json
from typing import Dict, Any, List


WALLS = ["WALL_1", "WALL_2", "WALL_3", "WALL_4"]

ORIENTATION_TO_EXTERNAL_WALL = {
    "north": "WALL_1",
    "south": "WALL_2",
    "east":  "WALL_3",
    "west":  "WALL_4",
}

def make_variant(
    base_zone: Dict[str, Any],
    zone_name: str,
    external_wall: str | None,
    external_wwr: float = 0.0,
) -> Dict[str, Any]:
    """
    external_wall:
      - one of WALL_1..WALL_4 -> that wall becomes facade (internal_fraction=0)
      - None -> internal-only (all internal_fraction=1, all wwr=0)
    """
    z = copy.deepcopy(base_zone)
    z["zone_name"] = zone_name

    # --- WWR: only external wall gets the input WWR, rest 0 ---
    z["wwr"] = {w: 0.0 for w in WALLS}
    if external_wall is not None:
        z["wwr"][external_wall] = float(external_wwr)

    # --- Surface parts: set internal_fraction per wall ---
    # Keep CEILING/FLOOR as in base (or default if missing)
    sp = z.get("surface_part", {})
    # ensure wall keys exist
    for w in WALLS:
        sp.setdefault(w, {"internal_fraction": 1.0, "side": "left"})
        sp[w]["internal_fraction"] = 1.0

    if external_wall is not None:
        sp[external_wall]["internal_fraction"] = 0.0  # facade

    z["surface_part"] = sp
    return z


def generate_5_rooms_from_one(
    base_zone: Dict[str, Any],
    wwr_by_orientation: Dict[str, float],
    name_prefix: str | None = None,
) -> List[Dict[str, Any]]:
    """
    wwr_by_orientation example:
      {"north": 0.5, "south": 0.4, "east": 0.3, "west": 0.2}
    """
    if name_prefix is None:
        name_prefix = base_zone.get("zone_name", "Room")

    out = []

    # 4 orientations
    for ori, ext_wall in ORIENTATION_TO_EXTERNAL_WALL.items():
        if ori not in wwr_by_orientation:
            raise ValueError(f"Missing WWR for '{ori}'. Provide it in wwr_by_orientation.")
        out.append(
            make_variant(
                base_zone=base_zone,
                zone_name=f"{name_prefix}_{ori.upper()}",
                external_wall=ext_wall,
                external_wwr=wwr_by_orientation[ori],
            )
        )

    # 1 internal-only
    out.append(
        make_variant(
            base_zone=base_zone,
            zone_name=f"{name_prefix}_INTERNAL_ONLY",
            external_wall=None,
            external_wwr=0.0,
        )
    )

    return out


# ---------------- Example usage ----------------
if __name__ == "__main__":
    base = {
        "zone_name": "Room_PHAERO",
        "zone_multiplier": 2,
        "zone_type": "3",
        "room_length": 7.0,
        "room_width": 7.0,
        "room_height": 4.0,
        "wwr": {"WALL_1": 0.5, "WALL_2": 0.0, "WALL_3": 0.0, "WALL_4": 0.0},
        "wall_constructions": {
            "WALL_1": {"internal": "IW_TB", "external": "AW_BE_MW"},
            "WALL_2": {"internal": "IW_TB", "external": "AW_BE_MW"},
            "WALL_3": {"internal": "IW_TB", "external": "AW_BE_MW"},
            "WALL_4": {"internal": "IW_TB", "external": "AW_BE_MW"},
        },
        "ceiling_constructions": {"internal": "Concrete floor 150mm", "external": "Concrete joist roof"},
        "floor_constructions": {"internal": "Concrete floor 150mm", "external": "Concrete floor 250mm"},
        "surface_part": {
            "WALL_1": {"internal_fraction": 0.0, "side": "left"},
            "WALL_2": {"internal_fraction": 1.0, "side": "left"},
            "WALL_3": {"internal_fraction": 1.0, "side": "left"},
            "WALL_4": {"internal_fraction": 1.0, "side": "left"},
            "CEILING": {"internal_fraction": 0.5},
            "FLOOR": {"internal_fraction": 0.5},
        },
        "glazing_type": "Double Clear Air 2-panes",
        "frame_area": 23.0,
        "frame_u_value": 1.0,
    }

    wwr_inputs = {"north": 0.5, "south": 0.4, "east": 0.3, "west": 0.2}

    zones5 = generate_5_rooms_from_one(base, wwr_inputs, name_prefix="Room_PHAERO")
    output_path = "zones_5_orientations.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(zones5, f, indent=2)

    print(f"Saved {len(zones5)} zones to {output_path}")
