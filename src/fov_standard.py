"""Standardized FOV calc (double buffer filter with circular shape)

Key Ideas:
1.) Max FOV range of up to 127 with 256 FOV bits (standardized)
2.) Faster building of FovMap using slope ranges
3.) Simpler FOV calculation with less branching
4.) Use bitflags instead of classes to store visible tiles
5.) Same slope range calculation for blocking and visible bits (no narrow/wide)
6.) No FovTile data is stored for the origin (observer's tile)
7.) Tilemap stores tiles in a single array
8.) Circular shape for more realistic FOV is baked into each FovMap

Saving to / loading from gzipped JSON:
- FovMaps is cached: loading from file is faster than generating new instances.
- file path: "fovmaps/fovmaps2d_standard_{max_radius}.fov"
- Field names are truncated to save space on file (~30% lower file size)
- JSON files are zipped to save even more space (~80% lower file size)
"""
import gzip
import json
import math
import pygame, pygame.freetype
from pathlib import Path
from pygame import Vector2
from pygame.color import Color
from pygame.freetype import Font
from pygame.surface import Surface
from helpers import (
    Blockers,
    Coords,
    Octant,
    FovLineType,
    QBits,
    boundary_radii,
    pri_sec_to_relative,
    to_tile_id
)
from map_drawing import (
    draw_player,
    draw_fov_line,
    draw_tile_at_cursor,
    draw_line_to_cursor,
    draw_floor,
    draw_north_wall,
    draw_west_wall,
    draw_structure
)
from typing import Dict, List, Tuple


class Settings:
    """Settings for Pygame."""

    def __init__(
        self,
        width: int,
        height: int,
        map_dims: Coords,
        font: Font,
        font_color: Color,
        radius: int = 63,
        max_radius: int = 63,
        tile_size: int = 64,
        subtiles_xy: int = 8,
        line_width: int = 1,
        qbits: QBits = QBits.Q64,
        fov_line_type: FovLineType = FovLineType.NORMAL,
        floor_color="steelblue2",
        floor_trim_color="steelblue4",
        fov_line_color="deepskyblue1",
        wall_color="seagreen3",
        wall_trim_color="seagreen4",
        structure_color="seagreen3",
        structure_trim_color="seagreen4",
        unseen_color="gray15",
        draw_tid: bool = False,
    ) -> None:
        if map_dims.x < 1 or map_dims.y < 1:
            raise ValueError("all map dimensions must be > 0!")

        self.width = width
        self.height = height
        self.xdims, self.ydims = map_dims
        self.tile_size = tile_size
        self.line_width = line_width
        self.subtiles_xy = subtiles_xy
        self.subtile_size = tile_size // subtiles_xy
        self.font = font
        self.font_color = font_color
        self.max_radius = min(max_radius, 127)
        self.radius = min(radius, self.max_radius)
        self.qbits = qbits
        self.fov_line_type = fov_line_type
        self.floor_color = Color(floor_color)
        self.fov_line_color = fov_line_color
        self.floor_trim_color = Color(floor_trim_color)
        self.wall_color = Color(wall_color)
        self.wall_trim_color = Color(wall_trim_color)
        self.structure_color = Color(structure_color)
        self.structure_trim_color = Color(structure_trim_color)
        self.unseen_color = unseen_color
        self.draw_tid = draw_tid


class Tile:
    """2D Tile, where `p1` is the reference point for drawing."""

    def __init__(self, tid: int, coords: Coords, ts: int, blockers: Blockers):
        self.tid = tid
        self.x = coords.x
        self.y = coords.y
        self.p1 = Vector2(coords.x * ts, coords.y * ts)
        self.structure = blockers.structure
        self.wall_n = blockers.wall_n
        self.wall_w = blockers.wall_w

    def __repr__(self) -> str:
        return f"T{self.tid}({self.x},{self.y}) S:{self.structure} N: {self.wall_n} W: {self.wall_w}"

    def to_coords(self) -> Tuple[int, int]:
        return (self.x, self.y)


class TileMap:
    """2D tilemap, taking a dictionary of blocked (x,y) coordinates."""

    def __init__(
        self,
        blocked: Dict[Tuple[int, int], Blockers],
        settings: Settings,
    ):
        ts = settings.tile_size
        xdims, ydims = settings.xdims, settings.ydims
        self.xdims = xdims
        self.ydims = ydims
        self.tiles = [
            Tile(
                to_tile_id(x, y, xdims),
                Coords(x, y),
                ts,
                blocked.get((x, y), Blockers()),
            )
            for y in range(ydims)
            for x in range(xdims)
        ]

    def tile_at(self, x: int, y: int) -> Tile:
        """Gets Tile at given location."""
        tid = x + y * self.xdims
        return self.tiles[tid]

    def show(self):
        tile_row = []
        row = 0
        for tile in self.tiles:
            tile_row.append(f"{tile}")
            if tile.y > row:
                row += 1
                print(" ".join(tile_row))
                tile_row.clear()


class FovMaps:
    """Holds `FovMap` instances for each value of FOV radius."""

    def __init__(self, maps: List) -> None:
        self.maps = maps

    @staticmethod
    def new(max_fov_radius: int):
        maps = [FovMap.new(r) for r in range(max_fov_radius)]

        return FovMaps(maps)

    @staticmethod
    def from_json(s: str):
        """Deserializes `FovMaps` from JSON string.

        Data is a list of dicts, each dict representing an `FovMap`.
        """
        jlist = json.loads(s)
        maps = [FovMap.from_dict(d) for d in jlist]

        return FovMaps(maps)

    @staticmethod
    def from_json_file(fp: str):
        """Deserializes `FovMaps` from JSON file at path `fp`.

        Data is a list of dicts, each dict representing an `FovMap`.
        """
        with open(fp, "r", encoding="utf-8") as f:
            jlist = json.load(f)
            maps = [FovMap.from_dict(d) for d in jlist]

        return FovMaps(maps)

    @staticmethod
    def from_json_file_compressed(fp):
        """Derializes FovMaps from gzip-compressed JSON file at path `fp`.
        
        Data is a list of dicts, each dict representing an `FovMap`.
        """
        
        with gzip.open(fp, 'rt', encoding='utf-8') as f:
            jlist = json.load(f)
            maps = [FovMap.from_dict(d) for d in jlist]

        return FovMaps(maps)

    def to_json(self) -> str:
        """Serializes `FovMap` to JSON string."""
        return json.dumps(self.to_list())

    def to_json_file(self, fp: str):
        """Serializes `FovMap` to JSON file with filepath `fp`."""
        with open(fp, "w", encoding="utf-8") as f:
            json.dump(self.to_list(), f)

    def to_json_file_compressed(self, fp):
        """Serializes FovMaps to gzip-compressed JSON file with filepath `fp`."""
        
        with gzip.open(fp, 'wt', encoding='utf-8') as f:
            json.dump(self.to_list(), f)  # type: ignore

    def to_list(self) -> List:
        """Converts `FovMaps` to list form for serialization.

        Consists of a list of 128 FovMaps in order of radius (0 to 127).
        """
        return [fov_map.to_dict() for fov_map in self.maps]


class FovMap:
    """2D FOV map of FovTiles, standardized to max FOV of 127 with 256 bits."""

    def __init__(self, o1, o2, o3, o4, o5, o6, o7, o8) -> None:
        self.octant_1 = o1
        self.octant_2 = o2
        self.octant_3 = o3
        self.octant_4 = o4
        self.octant_5 = o5
        self.octant_6 = o6
        self.octant_7 = o7
        self.octant_8 = o8

    @staticmethod
    def new(radius: int):
        o1 = FovOctant.new(radius, Octant.O1)
        o2 = FovOctant.new(radius, Octant.O2)
        o3 = FovOctant.new(radius, Octant.O3)
        o4 = FovOctant.new(radius, Octant.O4)
        o5 = FovOctant.new(radius, Octant.O5)
        o6 = FovOctant.new(radius, Octant.O6)
        o7 = FovOctant.new(radius, Octant.O7)
        o8 = FovOctant.new(radius, Octant.O8)

        return FovMap(o1, o2, o3, o4, o5, o6, o7, o8)

    @staticmethod
    def from_dict(d: Dict):
        """Creates `FovMap` from dictionary."""
        o1 = FovOctant.from_dict(d["o1"])
        o2 = FovOctant.from_dict(d["o2"])
        o3 = FovOctant.from_dict(d["o3"])
        o4 = FovOctant.from_dict(d["o4"])
        o5 = FovOctant.from_dict(d["o5"])
        o6 = FovOctant.from_dict(d["o6"])
        o7 = FovOctant.from_dict(d["o7"])
        o8 = FovOctant.from_dict(d["o8"])

        return FovMap(o1, o2, o3, o4, o5, o6, o7, o8)

    def to_dict(self) -> Dict:
        """Converts `FovMap` to dictionary form for serialization."""
        output = {
            "o1": self.octant_1.to_dict(),
            "o2": self.octant_2.to_dict(),
            "o3": self.octant_3.to_dict(),
            "o4": self.octant_4.to_dict(),
            "o5": self.octant_5.to_dict(),
            "o6": self.octant_6.to_dict(),
            "o7": self.octant_7.to_dict(),
            "o8": self.octant_8.to_dict(),
        }

        return output


class FovTile:
    """2D FOV Tile used in an FovOctant.

    An FOV tile is visible if at least one of its `tile_bits` is not blocked
    by `blocking_bits` in the FOV calculation. The same concept applies to
    West and North wall bits.

    ### Fields

    `dpri, dsec`: int
        Relative (pri,sec) coordinates of the FOV tile compared to FOV origin.
    `tile_bits_1`, `tile_bits_2`: int
        Lower/Upper bitflags spanning the Δsec/Δpri slope range of the tile.
    `north_wall_bits_1`, `north_wall_bits_2`: int
        Lower/Upper bitflags spanning the Δsec/Δpri slope range of the North wall.
    `west_wall_bits_1`, `west_wall_bits_2`: int
        Lower/Upper bitflags spanning the Δsec/Δpri slope range of the West wall.
    `buffer_ix`: int
        dsec index used to set buffer bits.
    `buffer_bits`: int
        bits required to be set in previous column for this tile to be unseen.
    """

    __slots__ = (
        "rx",
        "ry",
        "dpri",
        "dsec",
        "north_wall_bits_1",
        "north_wall_bits_2",
        "west_wall_bits_1",
        "west_wall_bits_2",
        "tile_bits_1",
        "tile_bits_2",
        "buffer_ix",
        "buffer_bits",
    )

    def __init__(
        self,
        rx,
        ry,
        dpri,
        dsec,
        north_wall_bits_1,
        north_wall_bits_2,
        west_wall_bits_1,
        west_wall_bits_2,
        tile_bits_1,
        tile_bits_2,
        buffer_ix,
        buffer_bits,
    ):
        self.rx = rx
        self.ry = ry
        self.dpri = dpri
        self.dsec = dsec
        self.north_wall_bits_1 = north_wall_bits_1
        self.north_wall_bits_2 = north_wall_bits_2
        self.west_wall_bits_1 = west_wall_bits_1
        self.west_wall_bits_2 = west_wall_bits_2
        self.tile_bits_1 = tile_bits_1
        self.tile_bits_2 = tile_bits_2
        self.buffer_ix = buffer_ix
        self.buffer_bits = buffer_bits

    def __repr__(self) -> str:
        return f"FovTile rel: ({self.rx},{self.ry})"

    @staticmethod
    def new(dpri: int, dsec: int, octant: Octant):
        # Octant-adjusted relative x/y
        rx, ry = pri_sec_to_relative(dpri, dsec, octant)

        # Slope ranges for tile and walls
        ts_lo, ts_hi = tile_slopes(dpri, dsec)

        match octant:
            case Octant.O1:
                ns_lo, ns_hi = tile_acute_slopes(dpri, dsec)
                ws_lo, ws_hi = tile_near_slopes(dpri, dsec)
            case Octant.O2:
                ns_lo, ns_hi = tile_near_slopes(dpri, dsec)
                ws_lo, ws_hi = tile_acute_slopes(dpri, dsec)
            case Octant.O3:
                ns_lo, ns_hi = tile_near_slopes(dpri, dsec)
                ws_lo, ws_hi = tile_obtuse_slopes(dpri, dsec)
            case Octant.O4:
                ns_lo, ns_hi = tile_acute_slopes(dpri, dsec)
                ws_lo, ws_hi = tile_far_slopes(dpri, dsec)
            case Octant.O5:
                ns_lo, ns_hi = tile_obtuse_slopes(dpri, dsec)
                ws_lo, ws_hi = tile_far_slopes(dpri, dsec)
            case Octant.O6:
                ns_lo, ns_hi = tile_far_slopes(dpri, dsec)
                ws_lo, ws_hi = tile_obtuse_slopes(dpri, dsec)
            case Octant.O7:
                ns_lo, ns_hi = tile_far_slopes(dpri, dsec)
                ws_lo, ws_hi = tile_acute_slopes(dpri, dsec)
            case Octant.O8:
                ns_lo, ns_hi = tile_obtuse_slopes(dpri, dsec)
                ws_lo, ws_hi = tile_near_slopes(dpri, dsec)

        n_wall_bits_lo, n_wall_bits_hi = quantized_slopes_256(ns_lo, ns_hi)
        w_wall_bits_lo, w_wall_bits_hi = quantized_slopes_256(ws_lo, ws_hi)
        tile_bits_lo, tile_bits_hi = quantized_slopes_256(ts_lo, ts_hi)

        # Blocking buffer bits
        buffer_ix = 2**dsec
        buffer_bits: int

        # Cardinal Alignment
        if dsec == 0:
            buffer_bits = buffer_ix

        # Diagonal Alignment
        elif dsec == dpri:
            buffer_bits = buffer_ix | buffer_ix >> 1

        # All other tiles
        else:
            buffer_bits = buffer_ix | buffer_ix >> 1

        return FovTile(
            int(rx),
            int(ry),
            dpri,
            dsec,
            n_wall_bits_lo,
            n_wall_bits_hi,
            w_wall_bits_lo,
            w_wall_bits_hi,
            tile_bits_lo,
            tile_bits_hi,
            buffer_ix,
            buffer_bits,
        )

    @staticmethod
    def from_dict(d: Dict):
        """Creates `FovTile` from dictionary."""
        return FovTile(
            d["rx"],
            d["ry"],
            d["dp"],
            d["ds"],
            d["nw1"],
            d["nw2"],
            d["ww1"],
            d["ww2"],
            d["tb1"],
            d["tb2"],
            d["bix"],
            d["bbs"],
        )

    def to_dict(self) -> Dict:
        """Returns `FovTile` in dictionary form for serialization."""
        return {
            "rx": self.rx,
            "ry": self.ry,
            "dp": self.dpri,
            "ds": self.dsec,
            "nw1": self.north_wall_bits_1,
            "nw2": self.north_wall_bits_2,
            "ww1": self.west_wall_bits_1,
            "ww2": self.west_wall_bits_2,
            "tb1": self.tile_bits_1,
            "tb2": self.tile_bits_2,
            "bix": self.buffer_ix,
            "bbs": self.buffer_bits,
        }


class FovOctant:
    """2D FOV Octant with TileMap coordinate translations and blocking bits.

    ### Fields

    `max_fov_ix`: List[int]
        Maximum FovCell index of x or y for a given radius. For example,
        max_fov_ix[22] gives the index of the farthest FovTile in FovOctant.tiles
        for a radius of 22.
    """

    def __init__(self, tiles: List[FovTile], max_fov_ix: List[int]):
        self.tiles = tiles
        self.max_fov_ix = max_fov_ix

    @staticmethod
    def new(radius: int, octant: Octant):
        tiles: List[FovTile] = []
        max_fov_ix: List[int] = [0]
        fov_ix = 0
        limit = radius * radius
        m = 0.5

        for dpri in range(1, radius + 1):
            for dsec in range(dpri + 1):
                if dpri == 0:
                    r = (dpri - m) * (dpri - m) + (dsec * dsec)
                else:
                    r = (dpri - m) * (dpri - m) + (dsec - m) * (dsec - m)

                if r < limit:
                    tile = FovTile.new(dpri, dsec, octant)
                    tiles.append(tile)
                    fov_ix += 1

            max_fov_ix.append(fov_ix)

        return FovOctant(tiles, max_fov_ix)

    @staticmethod
    def from_dict(d: Dict):
        tiles = [FovTile.from_dict(td) for td in d["t"]]
        max_fov_ix = [i for i in d["mfi"]]

        return FovOctant(tiles, max_fov_ix)

    def to_dict(self) -> Dict:
        """Converts `FovOctant` to dictionary form for serialization."""
        return {
            "t": [t.to_dict() for t in self.tiles],
            "mfi": self.max_fov_ix,
        }


def tile_near_slopes(dpri: int, dsec: int) -> Tuple[float, float]:
    """Slope range for nearest side of the tile as seen by the observer."""

    slope_lo = max((dsec - 0.5) / (dpri - 0.5), 0.0)
    slope_hi = min((dsec + 0.5) / (dpri - 0.5), 1.0)

    return slope_lo, slope_hi


def tile_far_slopes(dpri: int, dsec: int) -> Tuple[float, float]:
    """Slope range for farthest side of the tile as seen by the observer."""

    slope_lo = max((dsec - 0.5) / (dpri + 0.5), 0.0)
    slope_hi = min((dsec + 0.5) / (dpri + 0.5), 1.0)

    return slope_lo, slope_hi


def tile_obtuse_slopes(dpri: int, dsec: int) -> Tuple[float, float]:
    """Slope range for widest angle side of the tile as seen by the observer."""

    slope_lo = max((dsec + 0.5) / (dpri + 0.5), 0.0)
    slope_hi = min((dsec + 0.5) / (dpri - 0.5), 1.0)

    return slope_lo, slope_hi


def tile_acute_slopes(dpri: int, dsec: int) -> Tuple[float, float]:
    """Slope range for narrowest angle side of the tile as seen by the observer."""
    if dsec == 0:
        return 0.0, 0.0

    slope_lo = max((dsec - 0.5) / (dpri + 0.5), 0.0)
    slope_hi = min((dsec - 0.5) / (dpri - 0.5), 1.0)

    return slope_lo, slope_hi


def tile_slopes(dpri: int, dsec: int) -> Tuple[float, float]:
    """Returns low/high dsec/dpri slope for a tile."""
    if dsec == 0:
        return 0.0, min((dsec + 0.5) / (dpri - 0.5), 1.0)

    slope_lo = max((dsec - 0.5) / (dpri + 0.5), 0.0)
    slope_hi = min((dsec + 0.5) / (dpri - 0.5), 1.0)

    return slope_lo, slope_hi


#   ########    ####    ##    ##
#   ##        ##    ##  ##    ##
#   ######    ##    ##  ##    ##
#   ##        ##    ##   ##  ##
#   ##         ######      ##


def fov_calc(
    ox: int, oy: int, tilemap: TileMap, fov_map: FovMap, radius: int
) -> Dict[int, int]:
    """Returns tile IDs (and tile parts) seen from origin (ox, oy).

    Return value is in `TID:parts` form parts are a `CWNT` bitflag, where:
    - `C` = Corner wall part (visible if any wall present and visible)
    - `W` = West wall part (present and visible)
    - `N` = West wall part (present and visible)
    - `T` = Tile part (present and visible)

    ```
                     CWNT
    visible_parts: 0b0000
    ```

    ### Parameters

    `ox`, `oy`: int
        Origin coordinates of the current Unit.
    `radius`: int
        Current unit's FOV radius
    """
    tm = tilemap
    origin = tm.tile_at(ox, oy)
    xdims, ydims = tm.xdims, tm.ydims

    origin_visible = 0b0001

    if origin.wall_w > 0:
        origin_visible |= 0b1100
    if origin.wall_n > 0:
        origin_visible |= 0b1010

    visible_tiles = {origin.tid: origin_visible}

    # --- Octants 1-2 --- #
    max_x, max_y = boundary_radii(ox, oy, xdims, ydims, Octant.O1, radius)

    vis1 = get_visible_tiles_1(ox, oy, max_x, max_y, tm, fov_map.octant_1)
    update_visible_tiles(visible_tiles, vis1)

    vis2 = get_visible_tiles_2(ox, oy, max_y, max_x, tm, fov_map.octant_2)
    update_visible_tiles(visible_tiles, vis2)

    # --- Octants 3-4 --- #
    max_x, max_y = boundary_radii(ox, oy, xdims, ydims, Octant.O4, radius)

    vis3 = get_visible_tiles_3(ox, oy, origin, max_y, max_x, tm, fov_map.octant_3)
    update_visible_tiles(visible_tiles, vis3)

    vis4 = get_visible_tiles_4(ox, oy, origin, max_x, max_y, tm, fov_map.octant_4)
    update_visible_tiles(visible_tiles, vis4)

    # --- Octants 5-6 --- #
    max_x, max_y = boundary_radii(ox, oy, xdims, ydims, Octant.O5, radius)

    vis5 = get_visible_tiles_5(ox, oy, origin, max_x, max_y, tm, fov_map.octant_5)
    update_visible_tiles(visible_tiles, vis5)

    vis6 = get_visible_tiles_6(ox, oy, origin, max_y, max_x, tm, fov_map.octant_6)
    update_visible_tiles(visible_tiles, vis6)

    # --- Octants 7-8 --- #
    max_x, max_y = boundary_radii(ox, oy, xdims, ydims, Octant.O8, radius)

    vis7 = get_visible_tiles_7(ox, oy, origin, max_y, max_x, tm, fov_map.octant_7)
    update_visible_tiles(visible_tiles, vis7)

    vis8 = get_visible_tiles_8(ox, oy, max_x, max_y, tm, fov_map.octant_8)
    update_visible_tiles(visible_tiles, vis8)

    return visible_tiles


def get_visible_tiles_1(
    ox: int,
    oy: int,
    max_dpri: int,
    max_dsec: int,
    tilemap: TileMap,
    fov_octant: FovOctant,
) -> List[Tuple[int, int]]:
    """Returns list of visible tiles and subparts in Octant 1."""
    fov_tiles = fov_octant.tiles
    pri_ix_max = fov_octant.max_fov_ix[max_dpri]
    sec_ix_max = max_dsec
    blocked_bits_1: int = 0
    blocked_bits_2: int = 0
    visible_tiles = []

    # Blocking buffer bits for previous and current (primary) columns
    prev_buffer: int = 0b0
    curr_buffer: int = 0b0
    prev_pri: int = 0

    for fov_tile in fov_tiles[:pri_ix_max]:
        # Boundary and buffer filters
        if fov_tile.dsec > sec_ix_max:
            continue

        if fov_tile.dpri > prev_pri:
            prev_buffer = curr_buffer
            curr_buffer = 0
            prev_pri += 1

        buffer_bits = fov_tile.buffer_bits
        if buffer_bits & prev_buffer == buffer_bits:
            curr_buffer |= fov_tile.buffer_ix
            continue

        # Octant 1: check W -> N -> T
        tx, ty = ox + fov_tile.rx, oy + fov_tile.ry
        tile = tilemap.tile_at(tx, ty)
        visible_parts: int = 0

        w_wall_bits_1 = fov_tile.west_wall_bits_1
        w_wall_bits_2 = fov_tile.west_wall_bits_2
        n_wall_bits_1 = fov_tile.north_wall_bits_1
        n_wall_bits_2 = fov_tile.north_wall_bits_2
        tile_bits_1 = fov_tile.tile_bits_1
        tile_bits_2 = fov_tile.tile_bits_2

        if tile.wall_w and is_visible(
            w_wall_bits_1, w_wall_bits_2, blocked_bits_1, blocked_bits_2
        ):
            blocked_bits_1 |= w_wall_bits_1
            blocked_bits_2 |= w_wall_bits_2
            visible_parts |= 0b1100

        if tile.wall_n and is_visible(
            n_wall_bits_1, n_wall_bits_2, blocked_bits_1, blocked_bits_2
        ):
            blocked_bits_1 |= n_wall_bits_1
            blocked_bits_2 |= n_wall_bits_2
            visible_parts |= 0b1010

        if is_visible(tile_bits_1, tile_bits_2, blocked_bits_1, blocked_bits_2):
            visible_parts |= 0b0001

            if tile.structure:
                blocked_bits_1 |= tile_bits_1
                blocked_bits_2 |= tile_bits_2

        if visible_parts > 0:
            visible_tiles.append((tile.tid, visible_parts))

        if visible_parts & 1 == 0:
            curr_buffer |= fov_tile.buffer_ix

        prev_pri = fov_tile.dpri

    return visible_tiles


def get_visible_tiles_2(
    ox: int,
    oy: int,
    max_dpri: int,
    max_dsec: int,
    tilemap: TileMap,
    fov_octant: FovOctant,
) -> List[Tuple[int, int]]:
    """Returns list of visible tiles and subparts in Octant 2."""
    fov_tiles = fov_octant.tiles
    pri_ix_max = fov_octant.max_fov_ix[max_dpri]
    sec_ix_max = max_dsec
    blocked_bits_1: int = 0
    blocked_bits_2: int = 0
    visible_tiles = []

    # Blocking buffer bits for previous and current (primary) columns
    prev_buffer: int = 0b0
    curr_buffer: int = 0b0
    prev_pri: int = 0

    for fov_tile in fov_tiles[:pri_ix_max]:
        # Boundary and buffer filters
        if fov_tile.dsec > sec_ix_max:
            continue

        if fov_tile.dpri > prev_pri:
            prev_buffer = curr_buffer
            curr_buffer = 0
            prev_pri += 1

        buffer_bits = fov_tile.buffer_bits
        if buffer_bits & prev_buffer == buffer_bits:
            curr_buffer |= fov_tile.buffer_ix
            continue

        # Octant 2: check N -> W -> T
        tx, ty = ox + fov_tile.rx, oy + fov_tile.ry
        tile = tilemap.tile_at(tx, ty)
        visible_parts: int = 0

        w_wall_bits_1 = fov_tile.west_wall_bits_1
        w_wall_bits_2 = fov_tile.west_wall_bits_2
        n_wall_bits_1 = fov_tile.north_wall_bits_1
        n_wall_bits_2 = fov_tile.north_wall_bits_2
        tile_bits_1 = fov_tile.tile_bits_1
        tile_bits_2 = fov_tile.tile_bits_2

        if tile.wall_n and is_visible(
            n_wall_bits_1, n_wall_bits_2, blocked_bits_1, blocked_bits_2
        ):
            blocked_bits_1 |= n_wall_bits_1
            blocked_bits_2 |= n_wall_bits_2
            visible_parts |= 0b1010

        if tile.wall_w and is_visible(
            w_wall_bits_1, w_wall_bits_2, blocked_bits_1, blocked_bits_2
        ):
            blocked_bits_1 |= w_wall_bits_1
            blocked_bits_2 |= w_wall_bits_2
            visible_parts |= 0b1100

        if is_visible(tile_bits_1, tile_bits_2, blocked_bits_1, blocked_bits_2):
            visible_parts |= 0b0001

            if tile.structure:
                blocked_bits_1 |= tile_bits_1
                blocked_bits_2 |= tile_bits_2

        if visible_parts > 0:
            visible_tiles.append((tile.tid, visible_parts))

        if visible_parts & 1 == 0:
            curr_buffer |= fov_tile.buffer_ix

        prev_pri = fov_tile.dpri

    return visible_tiles


def get_visible_tiles_3(
    ox: int,
    oy: int,
    origin: Tile,
    max_dpri: int,
    max_dsec: int,
    tilemap: TileMap,
    fov_octant: FovOctant,
) -> List[Tuple[int, int]]:
    """Returns list of visible tiles and subparts in Octant 3."""
    fov_tiles = fov_octant.tiles
    pri_ix_max = fov_octant.max_fov_ix[max_dpri]
    sec_ix_max = max_dsec
    blocked_bits_1: int = 0
    blocked_bits_2: int = 0
    visible_tiles = []

    # Blocking buffer bits for previous and current (primary) columns
    prev_buffer: int = 0b0
    curr_buffer: int = 0b0
    prev_pri: int = 0

    # West wall blocking bits (upper bits = 2 ** 255) for origin tile
    if origin.wall_w:
        blocked_bits_2 |= 170141183460469231731687303715884105728

    for fov_tile in fov_tiles[:pri_ix_max]:
        # Boundary and buffer filters
        if fov_tile.dsec > sec_ix_max:
            continue

        if fov_tile.dpri > prev_pri:
            prev_buffer = curr_buffer
            curr_buffer = 0
            prev_pri += 1

        buffer_bits = fov_tile.buffer_bits
        if buffer_bits & prev_buffer == buffer_bits:
            curr_buffer |= fov_tile.buffer_ix
            continue

        # Octant 3: check N -> T -> W
        tx, ty = ox + fov_tile.rx, oy + fov_tile.ry
        tile = tilemap.tile_at(tx, ty)
        visible_parts: int = 0

        w_wall_bits_1 = fov_tile.west_wall_bits_1
        w_wall_bits_2 = fov_tile.west_wall_bits_2
        n_wall_bits_1 = fov_tile.north_wall_bits_1
        n_wall_bits_2 = fov_tile.north_wall_bits_2
        tile_bits_1 = fov_tile.tile_bits_1
        tile_bits_2 = fov_tile.tile_bits_2

        if tile.wall_n and is_visible(
            n_wall_bits_1, n_wall_bits_2, blocked_bits_1, blocked_bits_2
        ):
            blocked_bits_1 |= n_wall_bits_1
            blocked_bits_2 |= n_wall_bits_2
            visible_parts |= 0b1010

        if is_visible(tile_bits_1, tile_bits_2, blocked_bits_1, blocked_bits_2):
            visible_parts |= 0b0001

        if tile.wall_w and is_visible(
            w_wall_bits_1, w_wall_bits_2, blocked_bits_1, blocked_bits_2
        ):
            blocked_bits_1 |= w_wall_bits_1
            blocked_bits_2 |= w_wall_bits_2
            visible_parts |= 0b1100

        if visible_parts > 0:
            visible_tiles.append((tile.tid, visible_parts))

            if tile.structure:
                blocked_bits_1 |= tile_bits_1
                blocked_bits_2 |= tile_bits_2

        if visible_parts & 1 == 0:
            curr_buffer |= fov_tile.buffer_ix

        prev_pri = fov_tile.dpri

    return visible_tiles


def get_visible_tiles_4(
    ox: int,
    oy: int,
    origin: Tile,
    max_dpri: int,
    max_dsec: int,
    tilemap: TileMap,
    fov_octant: FovOctant,
) -> List[Tuple[int, int]]:
    """Returns list of visible tiles and subparts in Octant 4."""
    fov_tiles = fov_octant.tiles
    pri_ix_max = fov_octant.max_fov_ix[max_dpri]
    sec_ix_max = max_dsec
    blocked_bits_1: int = 0
    blocked_bits_2: int = 0
    visible_tiles = []

    # Blocking buffer bits for previous and current (primary) columns
    prev_buffer: int = 0b0
    curr_buffer: int = 0b0
    prev_pri: int = 0

    # If West wall present in origin, rest of octant is blocked
    if origin.wall_w:
        return visible_tiles

    for fov_tile in fov_tiles[:pri_ix_max]:
        # Boundary and buffer filters
        if fov_tile.dsec > sec_ix_max:
            continue

        if fov_tile.dpri > prev_pri:
            prev_buffer = curr_buffer
            curr_buffer = 0
            prev_pri += 1

        buffer_bits = fov_tile.buffer_bits
        if buffer_bits & prev_buffer == buffer_bits:
            curr_buffer |= fov_tile.buffer_ix
            continue

        # Octant 4: check N -> T -> W
        tx, ty = ox + fov_tile.rx, oy + fov_tile.ry
        tile = tilemap.tile_at(tx, ty)
        visible_parts: int = 0

        w_wall_bits_1 = fov_tile.west_wall_bits_1
        w_wall_bits_2 = fov_tile.west_wall_bits_2
        n_wall_bits_1 = fov_tile.north_wall_bits_1
        n_wall_bits_2 = fov_tile.north_wall_bits_2
        tile_bits_1 = fov_tile.tile_bits_1
        tile_bits_2 = fov_tile.tile_bits_2

        if tile.wall_n and is_visible(
            n_wall_bits_1, n_wall_bits_2, blocked_bits_1, blocked_bits_2
        ):
            blocked_bits_1 |= n_wall_bits_1
            blocked_bits_2 |= n_wall_bits_2
            visible_parts |= 0b1010

        if is_visible(tile_bits_1, tile_bits_2, blocked_bits_1, blocked_bits_2):
            visible_parts |= 0b0001

        if tile.wall_w and is_visible(
            w_wall_bits_1, w_wall_bits_2, blocked_bits_1, blocked_bits_2
        ):
            blocked_bits_1 |= w_wall_bits_1
            blocked_bits_2 |= w_wall_bits_2
            visible_parts |= 0b1100

        if visible_parts > 0:
            visible_tiles.append((tile.tid, visible_parts))

            if tile.structure:
                blocked_bits_1 |= tile_bits_1
                blocked_bits_2 |= tile_bits_2

        if visible_parts & 1 == 0:
            curr_buffer |= fov_tile.buffer_ix

        prev_pri = fov_tile.dpri

    return visible_tiles


def get_visible_tiles_5(
    ox: int,
    oy: int,
    origin: Tile,
    max_dpri: int,
    max_dsec: int,
    tilemap: TileMap,
    fov_octant: FovOctant,
) -> List[Tuple[int, int]]:
    """Returns list of visible tiles and subparts in Octant 5."""
    fov_tiles = fov_octant.tiles
    pri_ix_max = fov_octant.max_fov_ix[max_dpri]
    sec_ix_max = max_dsec
    blocked_bits_1: int = 0
    blocked_bits_2: int = 0
    visible_tiles = []

    # Blocking buffer bits for previous and current (primary) columns
    prev_buffer: int = 0b0
    curr_buffer: int = 0b0
    prev_pri: int = 0

    # If West wall present in origin, rest of octant is blocked
    if origin.wall_w:
        return visible_tiles

    for fov_tile in fov_tiles[:pri_ix_max]:
        # Boundary and buffer filters
        if fov_tile.dsec > sec_ix_max:
            continue

        if fov_tile.dpri > prev_pri:
            prev_buffer = curr_buffer
            curr_buffer = 0
            prev_pri += 1

        buffer_bits = fov_tile.buffer_bits
        if buffer_bits & prev_buffer == buffer_bits:
            curr_buffer |= fov_tile.buffer_ix
            continue

        # Octant 5: check T -> W -> N
        tx, ty = ox + fov_tile.rx, oy + fov_tile.ry
        tile = tilemap.tile_at(tx, ty)
        visible_parts: int = 0

        w_wall_bits_1 = fov_tile.west_wall_bits_1
        w_wall_bits_2 = fov_tile.west_wall_bits_2
        n_wall_bits_1 = fov_tile.north_wall_bits_1
        n_wall_bits_2 = fov_tile.north_wall_bits_2
        tile_bits_1 = fov_tile.tile_bits_1
        tile_bits_2 = fov_tile.tile_bits_2

        if is_visible(tile_bits_1, tile_bits_2, blocked_bits_1, blocked_bits_2):
            visible_parts |= 0b0001

        if tile.wall_n and is_visible(
            n_wall_bits_1, n_wall_bits_2, blocked_bits_1, blocked_bits_2
        ):
            blocked_bits_1 |= n_wall_bits_1
            blocked_bits_2 |= n_wall_bits_2
            visible_parts |= 0b1010

        if tile.wall_w and is_visible(
            w_wall_bits_1, w_wall_bits_2, blocked_bits_1, blocked_bits_2
        ):
            blocked_bits_1 |= w_wall_bits_1
            blocked_bits_2 |= w_wall_bits_2
            visible_parts |= 0b1100

        if visible_parts > 0:
            visible_tiles.append((tile.tid, visible_parts))

            if tile.structure:
                blocked_bits_1 |= tile_bits_1
                blocked_bits_2 |= tile_bits_2

        if visible_parts & 1 == 0:
            curr_buffer |= fov_tile.buffer_ix

        prev_pri = fov_tile.dpri

    return visible_tiles


def get_visible_tiles_6(
    ox: int,
    oy: int,
    origin: Tile,
    max_dpri: int,
    max_dsec: int,
    tilemap: TileMap,
    fov_octant: FovOctant,
) -> List[Tuple[int, int]]:
    """Returns list of visible tiles and subparts in Octant 6."""
    fov_tiles = fov_octant.tiles
    pri_ix_max = fov_octant.max_fov_ix[max_dpri]
    sec_ix_max = max_dsec
    blocked_bits_1: int = 0
    blocked_bits_2: int = 0
    visible_tiles = []

    # Blocking buffer bits for previous and current (primary) columns
    prev_buffer: int = 0b0
    curr_buffer: int = 0b0
    prev_pri: int = 0

    # If North wall present in origin, rest of octant is blocked
    if origin.wall_n:
        return visible_tiles

    for fov_tile in fov_tiles[:pri_ix_max]:
        # Boundary and buffer filters
        if fov_tile.dsec > sec_ix_max:
            continue

        if fov_tile.dpri > prev_pri:
            prev_buffer = curr_buffer
            curr_buffer = 0
            prev_pri += 1

        buffer_bits = fov_tile.buffer_bits
        if buffer_bits & prev_buffer == buffer_bits:
            curr_buffer |= fov_tile.buffer_ix
            continue

        # Octant 6: check T -> N -> W
        tx, ty = ox + fov_tile.rx, oy + fov_tile.ry
        tile = tilemap.tile_at(tx, ty)
        visible_parts: int = 0

        w_wall_bits_1 = fov_tile.west_wall_bits_1
        w_wall_bits_2 = fov_tile.west_wall_bits_2
        n_wall_bits_1 = fov_tile.north_wall_bits_1
        n_wall_bits_2 = fov_tile.north_wall_bits_2
        tile_bits_1 = fov_tile.tile_bits_1
        tile_bits_2 = fov_tile.tile_bits_2

        if is_visible(tile_bits_1, tile_bits_2, blocked_bits_1, blocked_bits_2):
            visible_parts |= 0b0001

        if tile.wall_n and is_visible(
            n_wall_bits_1, n_wall_bits_2, blocked_bits_1, blocked_bits_2
        ):
            blocked_bits_1 |= n_wall_bits_1
            blocked_bits_2 |= n_wall_bits_2
            visible_parts |= 0b1010

        if tile.wall_w and is_visible(
            w_wall_bits_1, w_wall_bits_2, blocked_bits_1, blocked_bits_2
        ):
            blocked_bits_1 |= w_wall_bits_1
            blocked_bits_2 |= w_wall_bits_2
            visible_parts |= 0b1100

        if visible_parts > 0:
            visible_tiles.append((tile.tid, visible_parts))

            if tile.structure:
                blocked_bits_1 |= tile_bits_1
                blocked_bits_2 |= tile_bits_2

        if visible_parts & 1 == 0:
            curr_buffer |= fov_tile.buffer_ix

        prev_pri = fov_tile.dpri

    return visible_tiles


def get_visible_tiles_7(
    ox: int,
    oy: int,
    origin: Tile,
    max_dpri: int,
    max_dsec: int,
    tilemap: TileMap,
    fov_octant: FovOctant,
) -> List[Tuple[int, int]]:
    """Returns list of visible tiles and subparts in Octant 7."""
    fov_tiles = fov_octant.tiles
    pri_ix_max = fov_octant.max_fov_ix[max_dpri]
    sec_ix_max = max_dsec
    blocked_bits_1: int = 0
    blocked_bits_2: int = 0
    visible_tiles = []

    # Blocking buffer bits for previous and current (primary) columns
    prev_buffer: int = 0b0
    curr_buffer: int = 0b0
    prev_pri: int = 0

    # If North wall present in origin, rest of octant is blocked
    if origin.wall_n:
        return visible_tiles

    for fov_tile in fov_tiles[:pri_ix_max]:
        # Boundary and buffer filters
        if fov_tile.dsec > sec_ix_max:
            continue

        if fov_tile.dpri > prev_pri:
            prev_buffer = curr_buffer
            curr_buffer = 0
            prev_pri += 1

        buffer_bits = fov_tile.buffer_bits
        if buffer_bits & prev_buffer == buffer_bits:
            curr_buffer |= fov_tile.buffer_ix
            continue

        # Octant 7: check W -> T -> N
        tx, ty = ox + fov_tile.rx, oy + fov_tile.ry
        tile = tilemap.tile_at(tx, ty)
        visible_parts: int = 0

        w_wall_bits_1 = fov_tile.west_wall_bits_1
        w_wall_bits_2 = fov_tile.west_wall_bits_2
        n_wall_bits_1 = fov_tile.north_wall_bits_1
        n_wall_bits_2 = fov_tile.north_wall_bits_2
        tile_bits_1 = fov_tile.tile_bits_1
        tile_bits_2 = fov_tile.tile_bits_2

        if tile.wall_w and is_visible(
            w_wall_bits_1, w_wall_bits_2, blocked_bits_1, blocked_bits_2
        ):
            blocked_bits_1 |= w_wall_bits_1
            blocked_bits_2 |= w_wall_bits_2
            visible_parts |= 0b1100

        if is_visible(tile_bits_1, tile_bits_2, blocked_bits_1, blocked_bits_2):
            visible_parts |= 0b0001

        if tile.wall_n and is_visible(
            n_wall_bits_1, n_wall_bits_2, blocked_bits_1, blocked_bits_2
        ):
            blocked_bits_1 |= n_wall_bits_1
            blocked_bits_2 |= n_wall_bits_2
            visible_parts |= 0b1010

        if visible_parts > 0:
            visible_tiles.append((tile.tid, visible_parts))

            if tile.structure:
                blocked_bits_1 |= tile_bits_1
                blocked_bits_2 |= tile_bits_2

        if visible_parts & 1 == 0:
            curr_buffer |= fov_tile.buffer_ix

        prev_pri = fov_tile.dpri

    return visible_tiles


def get_visible_tiles_8(
    ox: int,
    oy: int,
    max_dpri: int,
    max_dsec: int,
    tilemap: TileMap,
    fov_octant: FovOctant,
) -> List[Tuple[int, int]]:
    """Returns list of visible tiles and subparts in Octant 8."""
    fov_tiles = fov_octant.tiles
    pri_ix_max = fov_octant.max_fov_ix[max_dpri]
    sec_ix_max = max_dsec
    blocked_bits_1: int = 0
    blocked_bits_2: int = 0
    visible_tiles = []

    # Blocking buffer bits for previous and current (primary) columns
    prev_buffer: int = 0b0
    curr_buffer: int = 0b0
    prev_pri: int = 0

    for fov_tile in fov_tiles[:pri_ix_max]:
        # Boundary and buffer filters
        if fov_tile.dsec > sec_ix_max:
            continue

        if fov_tile.dpri > prev_pri:
            prev_buffer = curr_buffer
            curr_buffer = 0
            prev_pri += 1

        buffer_bits = fov_tile.buffer_bits
        if buffer_bits & prev_buffer == buffer_bits:
            curr_buffer |= fov_tile.buffer_ix
            continue

        # Octant 8: check W -> T -> N
        tx, ty = ox + fov_tile.rx, oy + fov_tile.ry
        tile = tilemap.tile_at(tx, ty)
        visible_parts: int = 0

        w_wall_bits_1 = fov_tile.west_wall_bits_1
        w_wall_bits_2 = fov_tile.west_wall_bits_2
        n_wall_bits_1 = fov_tile.north_wall_bits_1
        n_wall_bits_2 = fov_tile.north_wall_bits_2
        tile_bits_1 = fov_tile.tile_bits_1
        tile_bits_2 = fov_tile.tile_bits_2

        if tile.wall_w and is_visible(
            w_wall_bits_1, w_wall_bits_2, blocked_bits_1, blocked_bits_2
        ):
            blocked_bits_1 |= w_wall_bits_1
            blocked_bits_2 |= w_wall_bits_2
            visible_parts |= 0b1100

        if is_visible(tile_bits_1, tile_bits_2, blocked_bits_1, blocked_bits_2):
            visible_parts |= 0b0001

        if tile.wall_n and is_visible(
            n_wall_bits_1, n_wall_bits_2, blocked_bits_1, blocked_bits_2
        ):
            blocked_bits_1 |= n_wall_bits_1
            blocked_bits_2 |= n_wall_bits_2
            visible_parts |= 0b1010

        if visible_parts > 0:
            visible_tiles.append((tile.tid, visible_parts))

            if tile.structure:
                blocked_bits_1 |= tile_bits_1
                blocked_bits_2 |= tile_bits_2

        if visible_parts & 1 == 0:
            curr_buffer |= fov_tile.buffer_ix

        prev_pri = fov_tile.dpri

    return visible_tiles


def get_tile_at_cursor(mx: int, my: int, tile_size: int) -> Coords:
    """Gets the coordinates of the Tile at the mouse cursor position."""
    tx = math.floor(mx / tile_size)
    ty = math.floor(my / tile_size)
    return Coords(tx, ty)


def is_visible(visible_1: int, visible_2: int, blocked_1: int, blocked_2: int) -> bool:
    """Returns `True` if the tile/part has 1+ visible bits not in FOV's blocked bits."""
    return (
        visible_1 - (visible_1 & blocked_1) > 0
        or visible_2 - (visible_2 & blocked_2) > 0
    )


def quantized_slopes_256(slope_lo: float, slope_hi: float) -> Tuple[int, int]:
    """Returns dpri/dsec slope in a 256-bit (int, int) paired bitfield.

    Used for blocking_bits and visible_bits, these slope ranges round the
    low slope up and the high slope down (narrow).
    """
    field_1: int = 0
    field_2: int = 0

    bit_lo = max(math.ceil(slope_lo * 255.0), 0)
    bit_hi = min(math.floor(slope_hi * 255.0), 255)

    for b in range(bit_lo, min(128, bit_hi + 1)):
        field_1 |= 2**b

    for b in range(max(128, bit_lo), bit_hi + 1):
        field_2 |= 2 ** (b - 128)

    return field_1, field_2


def update_visible_tiles(
    to_dict: Dict[int, int],
    from_list: List[Tuple[int, int]],
):
    """ "Updates full dictionary of visible tiles from per-octant list.

    Incoming list of tuples is in form (x, y, visible_tile).
    """
    for tid, visible_tile in from_list:
        current = to_dict.get(tid, 0b0000)
        current |= visible_tile
        to_dict[tid] = current


#   #######   #######      ##     ##    ##
#   ##    ##  ##    ##   ##  ##   ##    ##
#   ##    ##  #######   ##    ##  ## ## ##
#   ##    ##  ##   ##   ########  ###  ###
#   #######   ##    ##  ##    ##   ##  ##


def draw_map(
    screen: Surface,
    tilemap: TileMap,
    visible_tiles: Dict[int, int],
    settings: Settings,
):
    """Renders the Tilemap, accounting for FOV."""
    for tid, tile in enumerate(tilemap.tiles):
        visible_tile = visible_tiles.get(tid)
        if visible_tile:
            draw_tile(screen, tile, visible_tile, settings)


def draw_tile(screen: Surface, tile: Tile, visible_parts: int, settings: Settings):
    """Renders a visible 3D Tile on the map using `visible_parts` data.

    ```
                      CWNT
    visible_parts = 0b0000
    ```
    Where:
    - `C` = Corner (if a wall present)
    - `W` = West wall
    - `N` = North wall
    - `T` = Tile (and structure, if present)
    """
    p1 = tile.p1
    p1x, p1y = tile.p1
    s = settings
    w = s.line_width
    ts = s.tile_size
    sts = s.subtile_size
    trim_color = settings.floor_trim_color

    # Draw Tile (if not blocked by walls), and structure (if present)
    if visible_parts & 0b0001:
        # Draw subgrid
        for dx in range(1, settings.subtiles_xy):
            x1 = p1x + dx * sts
            y1 = p1y
            x2 = p1x + dx * sts
            y2 = p1y + ts
            pygame.draw.line(screen, trim_color, (x1, y1), (x2, y2))

        for dy in range(1, settings.subtiles_xy):
            x1 = p1x
            y1 = p1y + dy * sts
            x2 = p1x + ts
            y2 = p1y + dy * sts
            pygame.draw.line(screen, trim_color, (x1, y1), (x2, y2))

        draw_floor(screen, p1, ts, s.floor_color)

        if tile.structure:
            draw_structure(screen, p1, ts, w, s.structure_color, s.structure_trim_color)

        if tile.wall_n:
            draw_north_wall(screen, p1, ts, sts, w, s.wall_color, s.wall_trim_color)

        if tile.wall_w:
            draw_west_wall(screen, p1, ts, sts, w, s.wall_color, s.wall_trim_color)
    else:
        if visible_parts & 0b0010:
            draw_north_wall(screen, p1, ts, sts, w, s.wall_color, s.wall_trim_color)

        if visible_parts & 0b0100:
            draw_west_wall(screen, p1, ts, sts, w, s.wall_color, s.wall_trim_color)


#    ######      ##     ##    ##  ########
#   ##         ##  ##   ###  ###  ##
#   ##   ###  ##    ##  ## ## ##  ######
#   ##    ##  ########  ##    ##  ##
#    ######   ##    ##  ##    ##  ########


def run_game(tilemap: TileMap, settings: Settings):
    """Renders the FOV display using Pygame."""
    # --- Pygame setup --- #
    pygame.init()
    pygame.display.set_caption("2D standard FOV")
    screen = pygame.display.set_mode((settings.width, settings.height))
    pygame.key.set_repeat(0)
    clock = pygame.time.Clock()
    running = True

    # --- Player Setup --- #
    px, py = settings.xdims // 2, settings.ydims // 2

    # --- Map Setup --- #
    fov_maps_path = f"fovmaps/fovmaps2d_standard_{settings.max_radius}.fov"
        
    if Path(fov_maps_path).exists():
        print(f"'{fov_maps_path}' exists! Loading FovMaps from file...")
        fov_maps = FovMaps.from_json_file_compressed(fov_maps_path)
        max_radius = len(fov_maps.maps)
        radius = min(settings.radius, max_radius)
    else:
        print(f"Generating FovMaps and caching to '{fov_maps_path}'...")
        max_radius = settings.max_radius
        radius = settings.radius
        fov_maps = FovMaps.new(max_radius)
        fov_maps.to_json_file_compressed(fov_maps_path)

    fov_map = fov_maps.maps[settings.radius]
    tile_size = settings.tile_size
    visible_tiles = fov_calc(px, py, tilemap, fov_map, radius)

    # --- HUD Setup --- #
    show_player_line = False
    show_fov_line = False
    show_cursor = True

    # --- Initial Draw --- #
    draw_map(screen, tilemap, visible_tiles, settings)
    draw_player(screen, px, py, tile_size)

    # --- Game Loop --- #
    while running:
        # Track user input to see if map needs to be redrawn (on input)
        redraw = False

        # --- Event Polling --- #
        # pygame.QUIT: Alt+F4 or Pressing 'X' in window corner
        # Handling keypresses with KEYDOWN ensures repeat delay works
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.dict["key"] == pygame.K_w and py > 0:
                    redraw = True
                    py -= 1
                if event.dict["key"] == pygame.K_s and py < tilemap.ydims - 1:
                    redraw = True
                    py += 1
                if event.dict["key"] == pygame.K_a and px > 0:
                    redraw = True
                    px -= 1
                if event.dict["key"] == pygame.K_d and px < tilemap.xdims - 1:
                    redraw = True
                    px += 1
                if event.dict["key"] == pygame.K_c:
                    show_cursor = not show_cursor
                    redraw = True
                if event.dict["key"] == pygame.K_f:
                    show_fov_line = not show_fov_line
                    redraw = True
                if event.dict["key"] == pygame.K_r:
                    show_player_line = not show_player_line
                    redraw = True
                if event.dict["key"] == pygame.K_MINUS and radius > 0:
                    redraw = True
                    radius -= 1
                    fov_map = fov_maps.maps[radius]
                if event.dict["key"] == pygame.K_EQUALS and radius < max_radius:
                    redraw = True
                    radius += 1
                    fov_map = fov_maps.maps[radius]

        # Check for mouse movement
        mdx, mdy = pygame.mouse.get_rel()
        if mdx != 0 or mdy != 0:
            redraw = True

        # --- Rendering --- #
        if redraw:
            # Fill the screen to clear previous frame
            screen.fill("black")
            mx, my = pygame.mouse.get_pos()
            visible_tiles = fov_calc(px, py, tilemap, fov_map, radius)
            draw_map(screen, tilemap, visible_tiles, settings)
            draw_player(screen, px, py, tile_size)

            tx, ty = get_tile_at_cursor(mx, my, tile_size)

            if show_fov_line:
                draw_fov_line(screen, px, py, tx, ty, settings)
            if show_cursor:
                draw_tile_at_cursor(screen, tx, ty, settings, line=False)
            if show_player_line:
                draw_line_to_cursor(screen, px, py, mx, my, settings)

        pygame.display.flip()

        clock.tick(30)  # FPS limit

    pygame.quit()


#   ##    ##     ##     ########  ##    ##
#   ###  ###   ##  ##      ##     ####  ##
#   ## ## ##  ##    ##     ##     ## ## ##
#   ##    ##  ########     ##     ##  ####
#   ##    ##  ##    ##  ########  ##    ##

if __name__ == "__main__":
    print("\n=====  2D Standard FOV Testing (Buffer Filter) =====\n")

    pygame.freetype.init()

    blocked: Dict[Tuple[int, int], Blockers] = {
        (4, 4): Blockers(wall_n=2),
        (5, 4): Blockers(wall_w=2),
        (8, 4): Blockers(wall_n=2, wall_w=2),
        (10, 4): Blockers(wall_n=2),
        (11, 4): Blockers(wall_n=2),
        (13, 7): Blockers(structure=True),
        (14, 6): Blockers(structure=True),
        (15, 0): Blockers(wall_w=2),
        (15, 1): Blockers(wall_n=2),
        (19, 4): Blockers(wall_n=2),
        (20, 3): Blockers(wall_w=2),
        (20, 4): Blockers(wall_n=2, wall_w=2),
    }

    settings = Settings(
        1280,
        720,
        Coords(16, 9),
        Font(None, size=16),
        Color("snow"),
        radius=5,
    )

    tilemap = TileMap(blocked, settings)
    run_game(tilemap, settings)
