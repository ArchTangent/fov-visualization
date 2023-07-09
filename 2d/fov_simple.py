"""2D FOV Visualization - Simple Method.

Key Ideas:
- Tiles either `block_sight` completely (over their entire span), or do not.
- FOV is divided into 8 parts called octants (not to be confused with geometric term).
- FOV angle ranges are quantized into 64, 128, or 256 subdivisions.
- It is ~10x faster to use pre-calculated values (in `FovTile`s). See `benchmarks` for more.
"""
import math
import pygame, pygame.freetype
from pygame import Vector2
from pygame.color import Color
from pygame.freetype import Font
from pygame.surface import Surface
from helpers import (
    to_tile_id,
    Coords,
    Octant,
    QBits,
    boundary_radii,
    max_fovtile_index,
    pri_sec_to_relative,
)
from typing import List, Tuple


class Settings:
    """Settings for Pygame."""

    def __init__(
        self,
        width: int,
        height: int,
        map_dims: Coords,
        tile_size: int,
        line_width: int,
        fov_radius: int,
        font: Font,
        font_color: Color,
        subtiles_xy: int = 8,
        floor_color="steelblue2",
        floor_trim_color="steelblue4",
        fov_line_color="slateblue1",
        fov_line_trim_color="slateblue3",
        structure_color="seagreen3",
        structure_trim_color="seagreen4",
        unseen_color="gray15",
        draw_tid: bool = False,
    ) -> None:
        self.width = width
        self.height = height
        self.map_dims = map_dims
        self.tile_size = tile_size
        self.line_width = line_width
        self.subtiles_xy = subtiles_xy
        self.subtile_size = tile_size // subtiles_xy
        self.font = font
        self.font_color = font_color
        self.fov_radius = fov_radius
        self.floor_color = Color(floor_color)
        self.fov_line_color = fov_line_color
        self.fov_line_trim_color = fov_line_trim_color
        self.floor_trim_color = Color(floor_trim_color)
        self.structure_color = Color(structure_color)
        self.structure_trim_color = Color(structure_trim_color)
        self.unseen_color = Color(unseen_color)
        self.draw_tid = draw_tid


class TileMap:
    """2D tilemap, taking a dictionary of blocked (x,y) coordinates.

    NOTE: direct access to Tilemap.tiles uses [y][x] order. Use `tile_at(x,y)` instead.
    """

    def __init__(self, dims: Coords, blocked: set[Tuple[int, int]]):
        self.xdims, self.ydims = dims
        ts = settings.tile_size

        self.tiles = [
            [
                Tile(
                    to_tile_id(x, y, self.xdims),
                    x,
                    y,
                    ts,
                    (x, y) in blocked,
                )
                for x in range(self.xdims)
            ]
            for y in range(self.ydims)
        ]

    def tile_at(self, x: int, y: int):
        """Gets Tile at given location"""
        return self.tiles[y][x]

    def tile_ix(self, x: int, y: int):
        """Gets Tile ID at given location"""
        return self.tiles[y][x].tid

    def show(self):
        for row in self.tiles:
            tile_row = [f"{t}" for t in row]
            print(" ".join(tile_row))


class Tile:
    """2D Tile."""

    def __init__(self, tid: int, x: int, y: int, ts: int, blocked: bool):
        self.tid = tid
        self.x = x
        self.y = y
        self.blocks_path = blocked
        self.blocks_sight = blocked
        # Reference point on the map for drawing
        self.p1 = Vector2(x * ts, y * ts)

    def __repr__(self) -> str:
        return f"C{self.tid}({self.x},{self.y})"

    def to_coords(self) -> Tuple[int, int]:
        return (self.x, self.y)


class TileSummary:
    """Summarizes key values for a tile at relative (x,y) values to observer."""

    def __init__(self, rx: int, ry: int) -> None:
        self.rx, self.ry = rx, ry
        self.slopes = slopes_by_relative_coords(rx, ry)
        self.q_block = quantized_slopes_wide(self.slopes[0], self.slopes[1], QBits.Q64)
        self.q_vis = quantized_slopes_narrow(self.slopes[0], self.slopes[1], QBits.Q64)

    def __repr__(self) -> str:
        return f"({self.ry},{self.rx}): {self.slopes}, block: {self.q_block}, vis: {self.q_vis}"


class FovMap:
    """2D FOV map of FovTiles used with TileMap to determine visible tiles."""

    def __init__(self, radius: int) -> None:
        if radius < 2:
            raise ValueError("Use max FOV radius of 2 or higher!")
        self.octant_1 = FovOctant(radius, Octant.O1)
        self.octant_2 = FovOctant(radius, Octant.O2)
        self.octant_3 = FovOctant(radius, Octant.O3)
        self.octant_4 = FovOctant(radius, Octant.O4)
        self.octant_5 = FovOctant(radius, Octant.O5)
        self.octant_6 = FovOctant(radius, Octant.O6)
        self.octant_7 = FovOctant(radius, Octant.O7)
        self.octant_8 = FovOctant(radius, Octant.O8)


class FovOctant:
    """2D FOV Octant with TileMap coordinate translations and blocking bits.

    `radius`: int
        Maximum in-game FOV radius.
    `octant`: Octant
        One of 8 Octants represented by this instance.
    """

    def __init__(self, radius: int, octant: Octant):
        self.tiles: List[FovTile] = []
        slice_threshold = 2
        tix = 1

        for dpri in range(1, radius):
            for dsec in range(slice_threshold):
                tile = FovTile(tix, dpri, dsec, octant)
                self.tiles.append(tile)
                tix += 1
            slice_threshold += 1


class FovTile:
    """2D FOV Tile used in an FovOctant.

    An FOV tile is visible if at least one of its `visible_bits` is not blocked
    by `blocked` bits in the FOV calculation.

    `tix`: int
        Tile index within the Octant and list of FOV tiles.
    `dpri, dsec`: int
        Relative (pri,sec) coordinates of the FOV tile compared to FOV origin.
    `visible_bits`: u64
        Bitflags spanning the visible Δsec/Δpri slope range for the tile.
    `blocking_bits`: u64
        Bitflags spanning the Δsec/Δpri slope range blocked by the tile (if wall present).
    """

    def __init__(self, tix: int, dpri: int, dsec: int, octant: Octant):
        # Blocking and visible bit ranges are all based on Octant 1
        slope_lo, slope_hi = slopes_by_relative_coords(dpri, dsec)

        # Blocking bits are wider than visible bits (restrictive)
        self.blocking_bit_lo, self.blocking_bit_hi = quantized_slopes_wide(
            slope_lo, slope_hi, QBits.Q64
        )
        self.blocking_bits = set_bits_from_range(
            self.blocking_bit_lo, self.blocking_bit_hi
        )

        self.visible_bit_lo, self.visible_bit_hi = quantized_slopes_narrow(
            slope_lo, slope_hi, QBits.Q64
        )
        self.visible_bits = set_bits_from_range(
            self.visible_bit_lo, self.visible_bit_hi
        )

        # Octant-adjusted relative x/y used to select tile in TileMap
        # dsec is needed for slice filter and bounds checks in FOV calc
        rx, ry = pri_sec_to_relative(dpri, dsec, octant)
        self.rx, self.ry = int(rx), int(ry)
        self.dsec = dsec
        self.tix = tix

    def __repr__(self) -> str:
        return f"FovTile {self.tix} rel: ({self.rx},{self.ry}), blk: {self.blocking_bit_lo}-{self.blocking_bit_hi}, vis: {self.visible_bit_lo}-{self.visible_bit_hi}"


#   ########    ####    ##    ##
#   ##        ##    ##  ##    ##
#   ######    ##    ##  ##    ##
#   ##        ##    ##   ##  ##
#   ##         ######      ##


def fov_calc(
    ox: int, oy: int, tilemap: TileMap, fov_map: FovMap, radius: int
) -> set[Tuple[int, int]]:
    """Returns visible tiles for the 2D FOV calculation using `FovTile`s.

    Notes:
    - check if tile is visible before applying blocking bits.
    - tiles can only add to blocked bits if they are visible.
    - the player's own tile is always visible.

    `ox`, `oy`: int
        Origin coordinates of the current Unit.
    `radius`: int
        Current unit's FOV radius.
    """
    visible_tiles = {(ox, oy)}
    tm = tilemap

    # --- Octants 1-8 --- #
    visible_tiles.update(
        get_visible_tiles(ox, oy, tm, fov_map.octant_1.tiles, Octant.O1, radius)
    )
    visible_tiles.update(
        get_visible_tiles(ox, oy, tm, fov_map.octant_2.tiles, Octant.O2, radius)
    )
    visible_tiles.update(
        get_visible_tiles(ox, oy, tm, fov_map.octant_3.tiles, Octant.O3, radius)
    )
    visible_tiles.update(
        get_visible_tiles(ox, oy, tm, fov_map.octant_4.tiles, Octant.O4, radius)
    )
    visible_tiles.update(
        get_visible_tiles(ox, oy, tm, fov_map.octant_5.tiles, Octant.O5, radius)
    )
    visible_tiles.update(
        get_visible_tiles(ox, oy, tm, fov_map.octant_6.tiles, Octant.O6, radius)
    )
    visible_tiles.update(
        get_visible_tiles(ox, oy, tm, fov_map.octant_7.tiles, Octant.O7, radius)
    )
    visible_tiles.update(
        get_visible_tiles(ox, oy, tm, fov_map.octant_8.tiles, Octant.O8, radius)
    )

    return visible_tiles


def fov_calc_columns(
    ox: int, oy: int, tilemap: TileMap, fov_map: FovMap, radius: int
) -> set[Tuple[int, int]]:
    """Returns visible tiles for the 2D FOV calculation using `FovTile`s. Uses column filter.

    Notes:
    - check if tile is visible before applying blocking bits.
    - tiles can only add to blocked bits if they are visible.
    - the player's own tile is always visible.

    `ox`, `oy`: int
        Origin coordinates of the current Unit.
    `radius`: int
        Current unit's FOV radius.
    """
    visible_tiles = {(ox, oy)}
    tm = tilemap

    # --- Octants 1-8 --- #
    visible_tiles.update(
        get_visible_tiles_columns(ox, oy, tm, fov_map.octant_1.tiles, Octant.O1, radius)
    )
    visible_tiles.update(
        get_visible_tiles_columns(ox, oy, tm, fov_map.octant_2.tiles, Octant.O2, radius)
    )
    visible_tiles.update(
        get_visible_tiles_columns(ox, oy, tm, fov_map.octant_3.tiles, Octant.O3, radius)
    )
    visible_tiles.update(
        get_visible_tiles_columns(ox, oy, tm, fov_map.octant_4.tiles, Octant.O4, radius)
    )
    visible_tiles.update(
        get_visible_tiles_columns(ox, oy, tm, fov_map.octant_5.tiles, Octant.O5, radius)
    )
    visible_tiles.update(
        get_visible_tiles_columns(ox, oy, tm, fov_map.octant_6.tiles, Octant.O6, radius)
    )
    visible_tiles.update(
        get_visible_tiles_columns(ox, oy, tm, fov_map.octant_7.tiles, Octant.O7, radius)
    )
    visible_tiles.update(
        get_visible_tiles_columns(ox, oy, tm, fov_map.octant_8.tiles, Octant.O8, radius)
    )

    return visible_tiles


def fov_calc_raw(
    ox: int, oy: int, tilemap: TileMap, radius: int
) -> set[Tuple[int, int]]:
    """Returns visible tiles for the 2D FOV calculation without `FovTile`s.

    Notes:
    - check if tile is visible before applying blocking bits.
    - tiles can only add to blocked bits if they are visible.
    - the player's own tile is always visible.

    `ox`, `oy`: int
        Origin coordinates of the current Unit.
    `radius`: int
        Current unit's FOV radius.
    """
    visible_tiles = {(ox, oy)}
    tm = tilemap

    # --- Octants 1-8 --- #
    visible_tiles.update(get_visible_tiles_raw(ox, oy, tm, Octant.O1, radius))
    visible_tiles.update(get_visible_tiles_raw(ox, oy, tm, Octant.O2, radius))
    visible_tiles.update(get_visible_tiles_raw(ox, oy, tm, Octant.O3, radius))
    visible_tiles.update(get_visible_tiles_raw(ox, oy, tm, Octant.O4, radius))
    visible_tiles.update(get_visible_tiles_raw(ox, oy, tm, Octant.O5, radius))
    visible_tiles.update(get_visible_tiles_raw(ox, oy, tm, Octant.O6, radius))
    visible_tiles.update(get_visible_tiles_raw(ox, oy, tm, Octant.O7, radius))
    visible_tiles.update(get_visible_tiles_raw(ox, oy, tm, Octant.O8, radius))

    return visible_tiles


def get_visible_tiles(
    ox: int,
    oy: int,
    tilemap: TileMap,
    fov_tiles: List[FovTile],
    octant: Octant,
    radius: int,
) -> List[Tuple[int, int]]:
    """Returns list of visible tiles in a given Octant using `FovTile`s.

    `ox`, `oy`: int
        Origin coordinates of the Unit for whom FOV is calculated.
    `radius`: int
        Current unit's FOV radius.
    """
    xdims, ydims = tilemap.xdims, tilemap.ydims
    blocked_bits: int = 0
    visible_tiles = []

    max_pri, max_sec = boundary_radii(ox, oy, xdims, ydims, octant, radius)
    pri_ix, sec_ix = max_fovtile_index(max_pri), max_sec + 1

    for fov_tile in fov_tiles[:pri_ix]:
        if fov_tile.dsec < sec_ix and tile_is_visible(
            fov_tile.visible_bits, blocked_bits
        ):
            tx, ty = ox + fov_tile.rx, oy + fov_tile.ry
            tile = tilemap.tile_at(tx, ty)
            visible_tiles.append((tx, ty))
            if tile.blocks_sight:
                blocked_bits |= fov_tile.blocking_bits

    return visible_tiles


def get_visible_tiles_columns(
    ox: int,
    oy: int,
    tilemap: TileMap,
    fov_tiles: List[FovTile],
    octant: Octant,
    radius: int,
) -> List[Tuple[int, int]]:
    """Returns list of visible tiles in a given Octant using `FovTile`s. Uses column filter.

    `ox`, `oy`: int
        Origin coordinates of the Unit for whom FOV is calculated.
    `radius`: int
        Current unit's FOV radius.
    """
    xdims, ydims = tilemap.xdims, tilemap.ydims
    blocked_bits: int = 0
    visible_tiles = []

    max_pri, max_sec = boundary_radii(ox, oy, xdims, ydims, octant, radius)
    pri_ix, sec_ix = max_fovtile_index(max_pri), max_sec + 1

    # Column/slice filter
    slice_num = 1
    slice_blocked = True

    for fov_tile in fov_tiles[:pri_ix]:
        dsec = fov_tile.dsec
        if dsec > slice_num:
            if slice_blocked:
                return visible_tiles
            slice_num += 1
            slice_blocked = True
        if dsec < sec_ix:
            if tile_is_visible(fov_tile.visible_bits, blocked_bits):
                slice_blocked = False
                tx, ty = ox + fov_tile.rx, oy + fov_tile.ry
                tile = tilemap.tile_at(tx, ty)
                visible_tiles.append((tx, ty))
                if tile.blocks_sight:
                    blocked_bits |= fov_tile.blocking_bits

    return visible_tiles


def get_visible_tiles_raw(
    ox: int, oy: int, tilemap: TileMap, octant: Octant, radius: int
) -> List[Tuple[int, int]]:
    """Returns list of visible tiles in a given Octant without `FovTile`s.

    `ox`, `oy`: int
        Origin coordinates of the Unit for whom FOV is calculated.
    `radius`: int
        Current unit's FOV radius.
    """
    xdims, ydims = tilemap.xdims, tilemap.ydims
    max_pri, max_sec = boundary_radii(ox, oy, xdims, ydims, octant, radius)
    visible_tiles = []
    blocked_bits = 0
    slice_target = 2

    if max_pri == 0:
        return visible_tiles

    # Get in-bounds Tile from tilemap using relative (x,y) value
    for pri in range(1, max_pri + 1):
        for sec in range(0, min(slice_target, max_sec + 1)):
            slope_lo, slope_hi = slopes_by_relative_coords(pri, sec)
            visible_bits = set_bits_from_range(
                *quantized_slopes_narrow(slope_lo, slope_hi, QBits.Q64)
            )
            # If visible and blocked, add to result and check blocking bits
            if tile_is_visible(visible_bits, blocked_bits):
                rx, ry = pri_sec_to_relative(pri, sec, octant)
                # rx, ry = octant_transform_int(max_pri, max_sec, Octant.O1, octant)
                tx, ty = ox + rx, oy + ry
                visible_tiles.append((tx, ty))
                tile = tilemap.tile_at(tx, ty)
                if tile.blocks_sight:
                    blocked_bits |= set_bits_from_range(
                        *quantized_slopes_wide(slope_lo, slope_hi, QBits.Q64)
                    )
        slice_target += 1

    return visible_tiles


def quantized_slopes_narrow(
    slope_lo: float, slope_hi: float, bits: QBits
) -> Tuple[int, int]:
    """Returns low/high narrow quantized slopes bits based on number of Q bits.

    A narrow slope rounds the low slope up and the high slope down.
    This is useful for visible bits in FOV calculation.

    See: "2D Dynamic FOV - Quantized 64-bit.ods" file.
    """
    match bits:
        case QBits.Q32:
            return math.ceil(slope_lo * 31.0), min(math.floor(slope_hi * 31.0), 31)
        case QBits.Q64:
            return math.ceil(slope_lo * 63.0), min(math.floor(slope_hi * 63.0), 63)
        case QBits.Q128:
            return max(math.ceil(slope_lo * 127.0), 0), min(
                math.floor(slope_hi * 127.0), 127
            )
        case QBits.Q256:
            return max(math.ceil(slope_lo * 255.0), 0), min(
                math.floor(slope_hi * 255.0), 255
            )


def quantized_slopes_wide(
    slope_lo: float, slope_hi: float, bits: QBits
) -> Tuple[int, int]:
    """Returns low/high wide quantized slopes bits based on number of Q bits.

    A wide slope rounds the low slope down and the high slope up.
    This is useful for blocking bits in FOV calculation.

    See: "2D Dynamic FOV - Quantized 64-bit.ods" file.
    """
    match bits:
        case QBits.Q32:
            return max(math.floor(slope_lo * 31.0), 0), min(
                math.ceil(slope_hi * 31.0), 31
            )
        case QBits.Q64:
            return max(math.floor(slope_lo * 63.0), 0), min(
                math.ceil(slope_hi * 63.0), 63
            )
        case QBits.Q128:
            return max(math.floor(slope_lo * 127.0), 0), min(
                math.ceil(slope_hi * 127.0), 127
            )
        case QBits.Q256:
            return max(math.floor(slope_lo * 255.0), 0), min(
                math.ceil(slope_hi * 255.0), 255
            )


def set_bits_from_range(lo_bit: int, hi_bit: int) -> int:
    """Sets visible and blocking bits from a low-high range."""
    if lo_bit > hi_bit:
        raise ValueError("lo_bit must be <= hi_bit!")

    bits = 0
    for bit in range(lo_bit, hi_bit + 1):
        bits |= 2**bit

    return bits


def slopes_by_relative_coords(dpri: int, dsec: int) -> Tuple[float, float]:
    """Returns low/high dsec/dpri slope for a 2D tile based on relative coords and Octant"""
    if dpri == dsec == 0:
        return 0.0, 1.0

    slope_lo = max((dsec - 0.5) / (dpri + 0.5), 0.0)
    slope_hi = min((dsec + 0.5) / (dpri - 0.5), 1.0)

    return slope_lo, slope_hi


def tile_is_visible(visible_bits: int, blocked_bits: int) -> bool:
    """Returns `True` if the tile has at least one visible bit not in FOV's blocked bits."""
    return visible_bits - (visible_bits & blocked_bits) > 0


#   #######   #######      ##     ##    ##
#   ##    ##  ##    ##   ##  ##   ##    ##
#   ##    ##  #######   ##    ##  ## ## ##
#   ##    ##  ##   ##   ########  ###  ###
#   #######   ##    ##  ##    ##   ##  ##


def draw_floor(
    screen: Surface, pr: Vector2, ts: int, width: int, color: Color, trim: Color
):
    """Draws a floor tile with reference point `pr` and tile size `ts`."""
    p1 = Vector2(pr.x, pr.y)
    p2 = Vector2(pr.x + ts, pr.y)
    p3 = Vector2(pr.x + ts, pr.y + ts)
    p4 = Vector2(pr.x, pr.y + ts)

    pygame.draw.lines(screen, color, True, [p1, p2, p3, p4], width=2)


def draw_structure(
    screen: Surface, pr: Vector2, ts: int, width: int, color: Color, trim: Color
):
    """Draws a structure in a tile with reference point `pr` and tile size `ts`."""
    p1 = Vector2(pr.x, pr.y)
    p2 = Vector2(pr.x + ts, pr.y)
    p3 = Vector2(pr.x + ts, pr.y + ts)
    p4 = Vector2(pr.x, pr.y + ts)

    pygame.draw.polygon(screen, color, [p1, p2, p3, p4])
    pygame.draw.lines(screen, trim, True, [p1, p2, p3, p4], width=width)


def draw_tile(screen: Surface, tile: Tile, settings: Settings):
    """Renders a visible 3D Tile on the map."""
    p1 = tile.p1
    p1x, p1y = tile.p1
    s = settings
    w = s.line_width
    ts = s.tile_size
    sts = s.subtile_size
    trim_color = settings.floor_trim_color

    # Draw grid if no structure present
    if not tile.blocks_sight:
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

        draw_floor(screen, p1, ts, w, s.floor_color, s.floor_trim_color)
    else:
        draw_structure(screen, p1, ts, w, s.structure_color, s.structure_trim_color)


def draw_map(
    tilemap: TileMap,
    visible_tiles: set,
    screen: Surface,
    settings: Settings,
):
    """Renders the Tilemap, accounting for FOV."""
    # Row is y; col is x
    for ty, row_data in enumerate(tilemap.tiles):
        for tx, tile in enumerate(row_data):
            if (tx, ty) in visible_tiles:
                draw_tile(screen, tile, settings)


def draw_player(screen: Surface, player_img: Surface, px: int, py: int, tile_size: int):
    """Renders the player (always visible) on the Tilemap."""
    screen.blit(player_img, (px * tile_size, py * tile_size))


#   #######   ########  ##    ##   ######   ##    ##
#   ##    ##  ##        ###   ##  ##    ##  ##    ##
#   #######   ######    ## ## ##  ##        ########
#   ##    ##  ##        ##   ###  ##    ##  ##    ##
#   #######   ########  ##    ##   ######   ##    ##

import random
import time


def time_fov(maps: int, radius: int, density: int, tries: int, seed: int):
    """Times visible tiles calc with FovTiles. 129x129 map w/64-fov Unit in center."""
    dims = Coords(128, 128)
    random.seed(seed)
    total_time = 0
    total_vt = 0

    for _ in range(maps):
        blocked = {
            (random.randint(0, 128), random.randint(0, 128)) for _ in range(density)
        }
        tm = TileMap(dims, blocked)
        fm = FovMap(radius)
        for trial in range(tries):
            start = time.time()
            vt = fov_calc(64, 64, tm, fm, radius)
            total_vt += len(vt)
            end = time.time()
            total_time += end - start

    print(f"Time (reg): {total_time} seconds")


def time_fov_columns(maps: int, radius: int, density: int, tries: int, seed: int):
    """Times visible tiles calc with FovTiles and column filter. 129x129 map w/64-fov Unit in center."""
    dims = Coords(128, 128)
    random.seed(seed)
    total_time = 0
    total_vt = 0

    for _ in range(maps):
        blocked = {
            (random.randint(0, 128), random.randint(0, 128)) for _ in range(density)
        }
        tm = TileMap(dims, blocked)
        fm = FovMap(radius)
        for trial in range(tries):
            start = time.time()
            vt = fov_calc_columns(64, 64, tm, fm, radius)
            total_vt += len(vt)
            end = time.time()
            total_time += end - start

    print(f"Time (columns): {total_time} seconds")


def time_fov_raw(maps: int, radius: int, density: int, tries: int, seed: int):
    """Times visible tiles calc without FovTiles. 129x129 map w/64-fov Unit in center."""
    random.seed(seed)
    total_time = 0
    total_vt = 0

    for _ in range(maps):
        blocked = {
            (random.randint(0, 128), random.randint(0, 128)) for _ in range(density)
        }
        tm = TileMap(settings.map_dims, blocked)
        fm = FovMap(radius)
        for trial in range(tries):
            start = time.time()
            vt = fov_calc_raw(64, 64, tm, radius)
            total_vt += len(vt)
            end = time.time()
            total_time += end - start

    print(f"Time (raw): {total_time} seconds")


#    ######      ##     ##    ##  ########
#   ##         ##  ##   ###  ###  ##
#   ##   ###  ##    ##  ## ## ##  ######
#   ##    ##  ########  ##    ##  ##
#    ######   ##    ##  ##    ##  ########


def run_game(blocked: set[Tuple[int, int]], settings: Settings):
    """Renders the FOV display using Pygame."""
    # --- Pygame setup --- #
    pygame.init()
    pygame.display.set_caption("2D Simple FOV")
    screen = pygame.display.set_mode((1280, 720))
    pygame.key.set_repeat(0)
    clock = pygame.time.Clock()
    running = True

    # --- Player Setup --- #
    px, py = (0, 0)
    player_img = pygame.image.load("assets/paperdoll_1.png").convert_alpha()
    radius = settings.fov_radius

    # --- Map Setup --- #
    tilemap = TileMap(settings.map_dims, blocked)
    tile_size = 64

    fov_map = FovMap(radius)
    visible_tiles = fov_calc(px, py, tilemap, fov_map, radius)

    # --- HUD Setup --- #

    # --- Initial Draw --- #
    draw_map(tilemap, visible_tiles, screen, settings)
    draw_player(screen, player_img, px, py, tile_size)

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

        # --- Rendering --- #
        if redraw:
            # fill the screen with a color to wipe away anything from last frame
            screen.fill("black")
            visible_tiles = fov_calc(px, py, tilemap, fov_map, radius)
            draw_map(tilemap, visible_tiles, screen, settings)
            draw_player(screen, player_img, px, py, tile_size)

        pygame.display.flip()

        clock.tick(60)  # FPS limit

    pygame.quit()


#   ##    ##     ##     ########  ##    ##
#   ###  ###   ##  ##      ##     ####  ##
#   ## ## ##  ##    ##     ##     ## ## ##
#   ##    ##  ########     ##     ##  ####
#   ##    ##  ##    ##  ########  ##    ##

if __name__ == "__main__":
    print("\n=====  2D Dynamic FOV Testing  =====\n")

    pygame.freetype.init()

    blocked = {
        (4, 4),
        (5, 4),
        (8, 4),
        (10, 4),
        (13, 7),
        (14, 6),
        (15, 0),
        (15, 1),
    }

    settings = Settings(
        1280,
        720,
        Coords(16, 9),
        64,
        1,
        64,
        Font(None, size=16),
        Color("snow"),
    )

    run_game(blocked, settings)
