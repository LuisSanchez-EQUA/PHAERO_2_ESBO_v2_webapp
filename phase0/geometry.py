import math
from typing import Dict


def fmt(value: float | int, ndigits: int = 1) -> str:
    text = f"{float(value):.{ndigits}f}".rstrip("0").rstrip(".")
    if "." not in text:
        text += ".0"
    if text.endswith("."):
        text += "0"
    return text


def build_schedules(code: str, zone_types_map: Dict[str, str]) -> Dict[str, str]:
    code_str = str(code).strip()
    if code_str not in zone_types_map:
        raise ValueError(f"Zone code '{code_str}' not found in zone_types.csv")

    type_name = zone_types_map[code_str]
    base = f"{code_str}. {type_name}"
    return {
        "occ_schedule": f"{base}_PersProfil",
        "occ_type": f"{base}_Std._Pers",
        "light_schedule": f"{base}_LichtProfil",
        "light_type": f"{base}_Std._Licht",
        "equip_schedule": f"{base}_GeräteProfil",
        "minvar_schedule": f"MinVar_{type_name}",
        "maxvar_schedule": f"MaxVar_{type_name}",
    }


def compute_floor_part(room_length, room_width, internal_fraction):
    room_length = float(room_length)
    room_width = float(room_width)
    fraction = max(0.0, min(1.0, float(internal_fraction)))

    scale = math.sqrt(fraction)
    dx = room_length * scale
    dy = room_width * scale
    x = (room_length - dx) / 2
    y = (room_width - dy) / 2

    return {
        "internal_fraction": fraction,
        "X": x,
        "Y": y,
        "DX": dx,
        "DY": dy,
    }


def compute_ceiling_part(room_length, room_width, internal_fraction):
    return compute_floor_part(room_length, room_width, internal_fraction)


def compute_wall_parts(
    wall_name: str,
    wall_w: float,
    wall_h: float,
    internal_fraction: float,
    wwr_ext: float,
    aspect_ratio: float = 1.6,
    sill_height: float = 0.9,
    head_clearance: float = 0.2,
    side_margin: float = 0.15,
    side: str = "left",
) -> Dict[str, Dict[str, float]]:
    wall_w = float(wall_w)
    wall_h = float(wall_h)
    internal_fraction = float(internal_fraction)
    wwr_ext = float(wwr_ext)
    aspect_ratio = float(aspect_ratio)
    sill_height = float(sill_height)
    head_clearance = float(head_clearance)
    side_margin = float(side_margin)

    area_surface = wall_w * wall_h
    area_internal = internal_fraction * area_surface
    area_external = area_surface - area_internal
    wwr_ext = max(0.0, min(1.0, wwr_ext))
    area_window = wwr_ext * area_external
    area_opaque_external = area_external - area_window

    width_internal = internal_fraction * wall_w
    width_external = wall_w - width_internal

    if area_window > 0:
        dy = (area_window / aspect_ratio) ** 0.5
        dx = aspect_ratio * dy
        dy = min(dy, wall_h - sill_height - head_clearance)
        dx = min(dx, max(width_external - 2 * side_margin, 0.0), width_external * 0.9)
    else:
        dx = dy = 0.0

    if side.lower() == "left":
        x_internal = 0.0
        x_external = width_internal
        x_window = x_external + (width_external - dx) / 2 if dx > 0 else x_external + width_external / 2
    else:
        x_internal = width_external
        x_external = 0.0
        x_window = (width_external - dx) / 2 if dx > 0 else width_external / 2

    return {
        "name": wall_name,
        "internal_opaque": {
            "area": area_internal,
            "X": x_internal,
            "Y": 0.0,
            "DX": width_internal,
            "DY": wall_h,
            "valid": 1.0,
        },
        "external_opaque": {
            "area": area_opaque_external,
            "X": x_external,
            "Y": 0.0,
            "DX": width_external,
            "DY": wall_h,
            "valid": 1.0,
        },
        "window": {
            "area": area_window,
            "X": x_window,
            "Y": sill_height,
            "DX": dx,
            "DY": dy,
            "valid": 1.0 if area_window > 0 else 0.0,
        },
    }
