from .geometry import fmt


def part1_room_parameters(room_length, room_width, room_height, room_area):
    return f"""  (:PAR :N ROOM-LENGTH :V {room_length} :S '(:DEFAULT NIL 2))
  (:PAR :N ROOM-WIDTH :V {room_width} :S '(:DEFAULT NIL 2))
  (:PAR :N ROOM-HEIGHT :V {room_height} :S '(:DEFAULT NIL 2))
  (:PAR :N ROOM-AREA :V {room_area} :S '(:DEFAULT NIL 2))
  (:PAR :N TOTAL-FLOOR-AREA)
  ((AGGREGATE :N INFILTRATION)
   (:PAR :N EX-LEAK-Z))
  ((AGGREGATE :N CENTRAL-SYSTEM)
   ((AGGREGATE :N VENTILATION)
    ((AGGREGATE :N "sf")
     (:PAR :N VOLFLRAT))
    ((AGGREGATE :N "rf")
     (:PAR :N VOLFLRAT))))
  ((AGGREGATE :N DISTRIBUTION)
   ((AGGREGATE :N DOMESTIC-HOT-WATER)
    (:PAR :N NOCC)))"""


def part2_zone_open(zone_name, zone_multiplier=1):
    return f"""
  (:ADD (ZONE :N "{zone_name}" :T ESBO-ROOM)
  (:PAR :N MULTIPLICITY :V {zone_multiplier})
   ((AGGREGATE :N THERMAL-BRIDGES)
    (:PAR :N EXT-WALLS)
    (:PAR :N EXTWALL-SLAB)
    (:PAR :N EXTWALL-INTWALL)
    (:PAR :N EXTWALL-CORN)
    (:PAR :N WIN-PERIM)
    (:PAR :N DOOR-PERIM)
    (:PAR :N ROOF)
    (:PAR :N SLAB)
    (:PAR :N BALCONY)
    (:PAR :N INTWALL-SLAB)
    (:PAR :N INTWALL-ROOF)
    (:PAR :N EXTWALL-INCORN)
    (:PAR :N ROOF-INCORN)
    (:PAR :N SLAB-INCORN)
    (:PAR :N EXT-WALLS-AREA)
    (:PAR :N EXTWALL-SLAB-LEN)
    (:PAR :N EXTWALL-CORN-LEN)
    (:PAR :N WIN-PERIM-LEN))"""


def part3_geometry(room_height, room_length, room_width, zone_volume, extsurf_area, facade_area):
    return f"""
   ((AGGREGATE :N GEOMETRY)
    (:PAR :N CEILING-HEIGHT :V {room_height})
    (:PAR :N ORIGIN :S '(:DEFAULT T 2))
    (:PAR :N NCORN :S '(:DEFAULT T 2))
    (:PAR :N CORNERS :V #2A((0.0 {room_length}) ({room_width} {room_length}) ({room_width} 0.0) (0.0 0.0)) :S '(:DEFAULT #S(MS-SPARSE DEFAULT-VALUE T DIMENSION 2 VALUE ((1 (2)) (2 (1) (2)) (3 (1)))) 2))
    (:PAR :N NET_FLOOR_AREA)
    (:PAR :N ZONE-VOLUME :V {zone_volume})
    (:PAR :N EXTSURF-AREA :V {extsurf_area})
    (:PAR :N FACADE-AREA :V {facade_area}))"""


def part4_zone_units(cav_supply, cav_return):
    return f"""
   ((AGGREGATE :N ZONE-UNITS)
    ((AGGREGATE :N HEATING :T ESBO-IDEAL-HEATER)
     (:PAR :N COP))
    ((AGGREGATE :N COOLING :T ESBO-IDEAL-COOLER)
     (:PAR :N COP))
    ((AGGREGATE :N VENTILATION :T ESBO-ZONE-VENT)
     (:PAR :N CAV-SUPPLY :V {cav_supply})
     (:PAR :N CAV-RETURN :V {cav_return})
     (:PAR :N VAV-CONTROL :F 2560)))"""


def part5_internal_gains(schedules):
    return f"""
   ((AGGREGATE :N INTERNAL-GAINS :T ESBO-INTERNAL-GAINS)
    (:RES :N OCC-SCHEDULE :V "{schedules['occ_schedule']}")
    (:TRES :N OCC-TYPE :V "{schedules['occ_type']}")
    (:RES :N LIGHT-SCHEDULE :V "{schedules['light_schedule']}")
    (:TRES :N LIGHT-TYPE :V "{schedules['light_type']}")
    (:RES :N EQUIP-SCHEDULE :V "{schedules['equip_schedule']}"))"""


def part6_indoor_climate(schedules):
    return f"""
   ((AGGREGATE :N INDOOR-CLIMATE :T ESBO-INDOOR-CLIMATE)
    (:PAR :N HEATING-SETPOINT :F 2560)
    (:PAR :N COOLING-SETPOINT :F 2560)
    (:PAR :N HEATING-SETPOINT-OFF :F 2560)
    (:PAR :N COOLING-SETPOINT-OFF :F 2560)
    (:ORES :N THERMOSTAT_MIN_SCHEDULE :V "{schedules['minvar_schedule']}")
    (:ORES :N THERMOSTAT_MAX_SCHEDULE :V "{schedules['maxvar_schedule']}"))"""


def part7_floor(floor_int, floor_ext, floor_data, room_length, room_width):
    if floor_data["internal_fraction"] > 0:
        subwall_block = f"""    ((SUBWALL :N "surface-part" :T ESBO-SURFACE-PART)
     (:PAR :N X :V {fmt(floor_data["X"])})
     (:PAR :N Y :V {fmt(floor_data["Y"])})
     (:PAR :N DX :V {fmt(floor_data["DX"])})
     (:PAR :N DY :V {fmt(floor_data["DY"])})
     (:PAR :N IF_NOT_CONNECTED :KV (ADIABATIC FIX_TEMP SIMILAR_OFFSET FACADE GROUND))
     (:RES :N CONSTRUCTION_INTERNAL :V "{floor_ext}")
     (:RES :N CONSTRUCTION_EXTERNAL :V "{floor_ext}"))"""
    else:
        subwall_block = ""

    return f"""
   ((ENCLOSING-ELEMENT :N FLOOR :T FLOOR :INDEX -2000 :NBSF (1 2 3 4))
    ((AGGREGATE :N GEOMETRY)
     (:PAR :N CORNERS :V #2A((0.0 {room_length} 0.0) ({room_width} {room_length} 0.0) ({room_width} 0.0 0.0) (0.0 0.0 0.0))))
    (:RES :N CONSTRUCTION_INTERNAL :V "{floor_int}")
    (:RES :N CONSTRUCTION_EXTERNAL :V "{floor_ext}")
{subwall_block})"""


def part8_ceiling(ceil_int, ceil_ext, ceiling_data, room_length, room_width, room_height):
    if ceiling_data["internal_fraction"] > 0:
        subwall_block = f"""    ((SUBWALL :N "surface-part" :T ESBO-SURFACE-PART)
     (:PAR :N X :V {fmt(ceiling_data["X"])})
     (:PAR :N Y :V {fmt(ceiling_data["Y"])})
     (:PAR :N DX :V {fmt(ceiling_data["DX"])})
     (:PAR :N DY :V {fmt(ceiling_data["DY"])})
     (:PAR :N IF_NOT_CONNECTED :KV (ADIABATIC FIX_TEMP SIMILAR_OFFSET FACADE GROUND))
     (:RES :N CONSTRUCTION_INTERNAL :V "{ceil_int}")
     (:RES :N CONSTRUCTION_EXTERNAL :V "{ceil_ext}"))"""
    else:
        subwall_block = ""

    return f"""
   ((ENCLOSING-ELEMENT :N CEILING :T CEILING :INDEX -1000 :NBSF (3 2 1 4))
    ((AGGREGATE :N GEOMETRY)
     (:PAR :N CORNERS :V #2A((0.0 0.0 {room_height}) ({room_width} 0.0 {room_height}) ({room_width} {room_length} {room_height}) (0.0 {room_length} {room_height}))))
    (:RES :N CONSTRUCTION_INTERNAL :V "{ceil_int}")
    (:RES :N CONSTRUCTION_EXTERNAL :V "{ceil_ext}")
{subwall_block})"""


def wall_block(
    wall_name,
    wall_data,
    wall_index,
    nbsf,
    room_length,
    room_width,
    room_height,
    wall_int,
    wall_ext,
    frame_area,
    frame_u,
    glazing,
    shading_type,
):
    if wall_name == "WALL_1":
        corners = f"#2A((0.0 {room_length} {room_height}) ({room_width} {room_length} {room_height}) ({room_width} {room_length} 0) (0.0 {room_length} 0))"
    elif wall_name == "WALL_2":
        corners = f"#2A(({room_width} {room_length} {room_height}) ({room_width} 0.0 {room_height}) ({room_width} 0.0 0) ({room_width} {room_length} 0))"
    elif wall_name == "WALL_3":
        corners = f"#2A(({room_width} 0.0 {room_height}) (0.0 0.0 {room_height}) (0.0 0.0 0) ({room_width} 0.0 0))"
    elif wall_name == "WALL_4":
        corners = f"#2A((0.0 0.0 {room_height}) (0.0 {room_length} {room_height}) (0.0 {room_length} 0) (0.0 0.0 0))"
    else:
        corners = ""

    if wall_data.get("wwr", 1.0) > 0:
        window_block = f"""    ((CE-WINDOW :N "window" :T ESBO-DETWIN)
     (:PAR :N X :V {fmt(wall_data['window']['X'])})
     (:PAR :N Y :V {fmt(wall_data['window']['Y'])})
     (:PAR :N DX :V {fmt(wall_data['window']['DX'])})
     (:PAR :N DY :V {fmt(wall_data['window']['DY'])})
     (:PAR :N SHADING-TYPE :V {shading_type})
     (:RES :N SHADING-MODEL :F 0 :V "MY_SHADING1" :KV OUTSIDE-BLIND)
     (:PAR :N FRAME_AREA :V {fmt(frame_area)})
     (:PAR :N FRAME-U-VALUE :V {fmt(frame_u)})
     (:RES :N GLAZING :V "{glazing}"))"""
    else:
        window_block = ""

    if wall_data.get("internal_fraction", 1.0) > 0:
        subwall_block = f"""    ((SUBWALL :N "surface-part" :T ESBO-SURFACE-PART)
     (:PAR :N X :V {fmt(wall_data['internal_opaque']['X'])})
     (:PAR :N Y :V {fmt(wall_data['internal_opaque']['Y'])})
     (:PAR :N DX :V {fmt(wall_data['internal_opaque']['DX'])})
     (:PAR :N DY :V {fmt(wall_data['internal_opaque']['DY'])})
     (:PAR :N IF_NOT_CONNECTED :V ADIABATIC :KV (ADIABATIC FIX_TEMP SIMILAR_OFFSET FACADE GROUND))
     (:RES :N CONSTRUCTION_INTERNAL :V "{wall_int}")
     (:RES :N CONSTRUCTION_EXTERNAL :V "{wall_ext}"))"""
    else:
        subwall_block = ""

    return f"""
   ((ENCLOSING-ELEMENT :N {wall_name} :T WALL :INDEX {wall_index} :NBSF {nbsf})
    ((AGGREGATE :N GEOMETRY)
     (:PAR :N CORNERS :V {corners}))
    (:PAR :N FACE :F 32)
    (:PAR :N IF_NOT_CONNECTED :V FACADE)
    (:RES :N CONSTRUCTION_INTERNAL :V "{wall_int}")
    (:RES :N CONSTRUCTION_EXTERNAL :V "{wall_ext}")
    (:RES :N EXTERNAL_SURFACE :X :REF)
{window_block}
{subwall_block})"""


def part9_walls(
    walls,
    wall_int_map,
    wall_ext_map,
    room_length,
    room_width,
    room_height,
    frame_area,
    frame_u,
    glazing,
    shading_type,
):
    blocks = []
    for wall in walls:
        blocks.append(
            wall_block(
                wall_name=wall["name"],
                wall_data=wall["data"],
                wall_index=wall["index"],
                nbsf=wall["nbsf"],
                room_length=room_length,
                room_width=room_width,
                room_height=room_height,
                wall_int=wall_int_map[wall["name"]],
                wall_ext=wall_ext_map[wall["name"]],
                frame_area=frame_area,
                frame_u=frame_u,
                glazing=glazing,
                shading_type=shading_type,
            )
        )
    return "\n".join(blocks)


def part10_viewpoint():
    return """

   ((AGGREGATE :N VIEWPT :T VIEWPOINT)
    (:PAR :N POSITION :V #(20 -20 20))
    (:PAR :N FOCALPOINT :V #(1.25 6.0 1.30000007152557))))
    (:REMOVE "Room")
  ((AGGREGATE :N CENTRAL-SYSTEM)
   ((AGGREGATE :N VENTILATION)
    ((AGGREGATE :N "sf")
     (:PAR :N VOLFLRAT))
    ((AGGREGATE :N "rf")
     (:PAR :N VOLFLRAT))))
    )"""


def build_lisp_script(
    room_length,
    room_width,
    room_height,
    room_area,
    zone_volume,
    extsurf_area,
    facade_area,
    zone_name,
    zone_multiplier,
    cav_supply,
    cav_return,
    floor_int,
    floor_ext,
    ceil_int,
    ceil_ext,
    floor_data,
    ceiling_data,
    walls,
    wall_int_map,
    wall_ext_map,
    frame_area,
    frame_u,
    glazing,
    shading_type,
    schedules,
):
    return (
        f"""(:UPDATE [@]
{part1_room_parameters(room_length, room_width, room_height, room_area)}
{part2_zone_open(zone_name, zone_multiplier)}
{part3_geometry(room_height, room_length, room_width, zone_volume, extsurf_area, facade_area)}
{part4_zone_units(cav_supply, cav_return)}
{part5_internal_gains(schedules)}
{part6_indoor_climate(schedules)}
{part7_floor(floor_int, floor_ext, floor_data, room_length, room_width)}
{part8_ceiling(ceil_int, ceil_ext, ceiling_data, room_length, room_width, room_height)}
{part9_walls(
        walls=walls,
        wall_int_map=wall_int_map,
        wall_ext_map=wall_ext_map,
        room_length=room_length,
        room_width=room_width,
        room_height=room_height,
        frame_area=frame_area,
        frame_u=frame_u,
        glazing=glazing,
        shading_type=shading_type,
    )}
{part10_viewpoint()}
"""
    )
