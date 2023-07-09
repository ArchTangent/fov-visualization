"""2D FOV Visualization - Advanced Method.

New version that uses octant-specific logic.

Key Ideas:
- Walls are treated as axis-aligned lines along West and/or North side of a Tile.
- Structures are treated as axis-aligned rectangles spanning an entire Tile.
- As # of FOV bits goes up, FOV granularity and generation time go up. 64 is a good value.
- FOV is divided into 8 parts called octants (not to be confused with geometric term).
- Uses line-line and line-rectangle intersections to determine which tile are visible.
"""
import math
import pygame, pygame.freetype
from pygame import Vector2
from pygame.color import Color
from pygame.freetype import Font
from pygame.surface import Surface
from helpers import (
    Coords,
    Line,
    Octant,
    QBits,
    VisibleTile,
    boundary_radii,
    line_line_intersection,
    octant_transform_flt,
    pri_sec_to_relative,
    to_tile_id,
)
from lines import bresenham_full
from typing import List, Dict, Self, Tuple


class Settings:
    """Settings for Pygame."""

    def __init__(
        self,
        width: int,
        height: int,
        map_dims: Coords,
        tile_size: int,
        line_width: int,
        subtiles_xy: int,
        qbits: QBits,
        font: Font,
        font_color: Color,
        fov_radius: int = 63,
        floor_color="steelblue2",
        floor_trim_color="steelblue4",
        fov_line_color="slateblue1",
        fov_line_trim_color="slateblue3",
        wall_color="seagreen3",
        wall_trim_color="seagreen4",
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
        self.qbits = qbits
        self.font = font
        self.font_color = font_color
        self.fov_radius = fov_radius
        self.floor_color = Color(floor_color)
        self.fov_line_color = fov_line_color
        self.fov_line_trim_color = fov_line_trim_color
        self.floor_trim_color = Color(floor_trim_color)
        self.wall_color = Color(wall_color)
        self.wall_trim_color = Color(wall_trim_color)
        self.structure_color = Color(structure_color)
        self.structure_trim_color = Color(structure_trim_color)
        self.unseen_color = Color(unseen_color)
        self.draw_tid = draw_tid
        self.xdims, self.ydims = map_dims.x, map_dims.y


class Blockers:
    """FOV blocking data for TileMap construction."""

    def __init__(
        self,
        structure: int = 0,
        wall_n: int = 0,
        wall_w: int = 0,
    ) -> None:
        self.structure = structure
        self.wall_n = wall_n
        self.wall_w = wall_w


class TileMap:
    """2D tilemap, taking a dictionary of blocked (x,y) coordinates.

    NOTE: direct access to Tilemap.tiles uses [y][x] order. Use `tile_at(x,y)` instead.
    """

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
            [
                Tile(
                    to_tile_id(x, y, xdims),
                    Coords(x, y),
                    ts,
                    blocked.get((x, y), Blockers()),
                )
                for x in range(xdims)
            ]
            for y in range(ydims)
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

    def __init__(self, tid: int, coords: Coords, ts: int, blockers: Blockers):
        self.tid = tid
        self.x = coords.x
        self.y = coords.y
        # Reference point on the map for drawing
        self.p1 = Vector2(coords.x * ts, coords.y * ts)
        self.structure = blockers.structure
        self.wall_n = blockers.wall_n
        self.wall_w = blockers.wall_w

    def __repr__(self) -> str:
        return f"T{self.tid}({self.x},{self.y}) S:{self.structure} N: {self.wall_n} W: {self.wall_w}"

    def to_coords(self) -> Tuple[int, int]:
        return (self.x, self.y)


def get_tile_at_cursor(mx: int, my: int, tile_size: int) -> Coords:
    """Gets the coordinates of the Tile at the mouse cursor position."""
    tx = math.floor(mx / tile_size)
    ty = math.floor(my / tile_size)
    return Coords(tx, ty)


class FovMap:
    """2D FOV map of FovTiles used with TileMap to determine visible tiles.

    `qbits`: int
        Number of bits used to quantize FOV lines. Higher = more granular FOV.
    """

    def __init__(self, qbits: QBits) -> None:
        self.octant_1 = FovOctant(Octant.O1, qbits)
        self.octant_2 = FovOctant(Octant.O2, qbits)
        self.octant_3 = FovOctant(Octant.O3, qbits)
        self.octant_4 = FovOctant(Octant.O4, qbits)
        self.octant_5 = FovOctant(Octant.O5, qbits)
        self.octant_6 = FovOctant(Octant.O6, qbits)
        self.octant_7 = FovOctant(Octant.O7, qbits)
        self.octant_8 = FovOctant(Octant.O8, qbits)


class FovOctant:
    """2D FOV Octant with TileMap coordinate translations and blocking bits.

    This version includes the observer's own tile (radius 0) due to walls.

    ### Parameters

    `qbits`: int
        Number of bits used to quantize FOV lines. Higher = more granular FOV.
        For qbits = 64, the FOV radius is from 0-63.
    `octant`: Octant
        One of 8 Octants represented by this instance.

    ### Fields

    `max_fov_ix`: List[int]
        Maximum FovCell index of x or y for a given radius. For example,
        max_fov_ix[22] gives the index of the farthest FovTile in FovOctant.tiles
        for a radius of 22.
    """

    def __init__(self, octant: Octant, qbits: QBits):
        self.tiles: List[FovTile] = []
        self.max_fov_ix: List[int] = []
        slice_threshold = 1
        tix = 0

        radius = qbits.value - 1
        fov_lines = FovLines(radius, octant)

        for dpri in range(radius + 1):
            self.max_fov_ix.append(tix)

            for dsec in range(slice_threshold):
                tile = FovTile(tix, dpri, dsec, octant, fov_lines)
                self.tiles.append(tile)
                tix += 1
            slice_threshold += 1


class FovLines:
    """List of (x1, y1, x2, y2) start/end points for FOV lines in range [0, radius].

    There is one FOV bit / FOV index for each FOV line. If the number of Qbits is 63,
    there are 64 FOV bits, one bit for each FOV line.

    FOV lines are fired from the xy center of the tile, (0.5, 0.5).
    """

    def __init__(self, radius: int, octant: Octant) -> None:
        self.lines: List[Line] = []
        pri = radius

        for sec in range(radius + 1):
            dpri, dsec = octant_transform_flt(pri, sec, Octant.O1, octant)
            line = Line(0.5, 0.5, 0.5 + dpri, 0.5 + dsec)

            self.lines.append(line)


class FovTile:
    """2D FOV Tile used in an `FovOctant`.

    An FOV tile is visible if at least one of its `visible_bits` is not blocked
    by `blocked` bits in the FOV calculation.

    `tix`: int
        Tile index within the Octant and list of FOV tiles.
    `dpri, dsec`: int
        Relative (pri,sec) coordinates of the FOV tile compared to FOV origin.
    `subtiles_xy`: int
        Number of subtiles on x and y axes. If 8, there are (8x8 = 64) subtiles per tile.
    `visible_bits`: u64
        Bitflags spanning the visible Δsec/Δpri FIV lines for the tile.
    `blocking_bits`: u64
        Bitflags spanning the Δsec/Δpri FOV lines blocked by the tile (if wall present).
    `fov_lines`: FovLines
        Grouping of FOV lines for the given octant, used to get blocking and visible bits.
    """

    __slots__ = (
        "wall_n_bits",
        "wall_w_bits",
        "structure_bits",
        "wall_n_line",
        "wall_w_line",
        "structure_lines",
        "visible_bits",
        "rx",
        "ry",
        "dpri",
        "dsec",
        "tix",
    )

    def __init__(
        self, tix: int, dpri: int, dsec: int, octant: Octant, fov_lines: FovLines
    ):
        # Octant-adjusted relative x/y used to select tile in TileMap
        # dpri is needed for wall visibility calculations
        # dsec is needed for slice filter and bounds checks in FOV calc
        rx, ry = pri_sec_to_relative(dpri, dsec, octant)
        self.rx, self.ry = int(rx), int(ry)
        self.dpri = dpri
        self.dsec = dsec
        self.tix = tix

        wall_line_n = Line(rx, ry, rx + 1.0, ry)
        wall_line_w = Line(rx, ry, rx, ry + 1.0)
        structure_lines = self.structure_line_pair(rx, ry, octant)

        self.wall_n_line = wall_line_n
        self.wall_w_line = wall_line_w
        self.structure_lines = structure_lines
        self.wall_n_bits: int = 0
        self.wall_w_bits: int = 0
        self.structure_bits: int = 0
        self.visible_bits: int = 0

        # Set blocking and visible bits from walls and structures
        for ix, fov_line in enumerate(fov_lines.lines):
            bit_ix = 1 << ix

            if line_line_intersection(fov_line, wall_line_n):
                self.wall_n_bits |= bit_ix

            if line_line_intersection(fov_line, wall_line_w):
                self.wall_w_bits |= bit_ix

            if line_line_intersection(
                fov_line, structure_lines[0]
            ) or line_line_intersection(fov_line, structure_lines[1]):
                self.structure_bits |= bit_ix
                self.visible_bits |= bit_ix

    def __repr__(self) -> str:
        return f"FovTile {self.tix} rel: ({self.rx},{self.ry}), structure: {self.structure_lines} wall N/W: {self.wall_n_line}/{self.wall_w_line}"

    def structure_line_pair(
        self, rx: int, ry: int, octant: Octant
    ) -> Tuple[Line, Line]:
        """Returns two closest lines representing the structure for FOV calculation."""
        match octant:
            case Octant.O1 | Octant.O2:
                result = Line(rx, ry, rx + 1.0, ry), Line(rx, ry, rx, ry + 1.0)
            case Octant.O3 | Octant.O4:
                result = Line(rx, ry, rx + 1.0, ry), Line(
                    rx + 1.0, ry, rx + 1.0, ry + 1.0
                )
            case Octant.O5 | Octant.O6:
                result = Line(rx, ry + 1.0, rx + 1.0, ry + 1.0), Line(
                    rx + 1.0, ry, rx + 1.0, ry + 1.0
                )
            case Octant.O7 | Octant.O8:
                result = Line(rx, ry + 1.0, rx + 1.0, ry + 1.0), Line(
                    rx, ry, rx, ry + 1.0
                )

        return result


#   #######   #######      ##     ##    ##
#   ##    ##  ##    ##   ##  ##   ##    ##
#   ##    ##  #######   ##    ##  ## ## ##
#   ##    ##  ##   ##   ########  ###  ###
#   #######   ##    ##  ##    ##   ##  ##


def draw_tile(
    screen: Surface, tile: Tile, visible_tile: VisibleTile, settings: Settings
):
    """Renders a visible 3D Tile on the map."""
    p1 = tile.p1
    p1x, p1y = tile.p1
    s = settings
    w = s.line_width
    ts = s.tile_size
    sts = s.subtile_size
    trim_color = settings.floor_trim_color

    tile_seen = visible_tile.tile
    wall_n_seen = visible_tile.wall_n
    wall_w_seen = visible_tile.wall_w
    structure_seen = visible_tile.structure

    # Draw Tile (if not blocked by walls), and structure (if present)
    if tile_seen:
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

        draw_floor(screen, p1, ts, w, s.floor_color, s.floor_trim_color)

        if structure_seen:
            draw_structure(screen, p1, ts, w, s.structure_color, s.structure_trim_color)

        if wall_n_seen:
            draw_north_wall(screen, p1, ts, sts, w, s.wall_color, s.wall_trim_color)

        if wall_w_seen:
            draw_west_wall(screen, p1, ts, sts, w, s.wall_color, s.wall_trim_color)

    # Draw walls separately if Tile not seen
    else:
        # Draw N wall (if present)
        if wall_n_seen:
            draw_north_wall(screen, p1, ts, sts, w, s.wall_color, s.wall_trim_color)
        # Draw W wall (if present)
        if wall_w_seen:
            draw_west_wall(screen, p1, ts, sts, w, s.wall_color, s.wall_trim_color)


def draw_unseen_tile(screen: Surface, pr: Vector2, settings: Settings):
    """Renders an unseen tile on the map."""
    s = settings
    w = s.line_width
    color = s.unseen_color
    trim = s.unseen_color
    ts = s.tile_size

    p1 = Vector2(pr.x, pr.y)
    p2 = Vector2(pr.x + ts, pr.y)
    p3 = Vector2(pr.x + ts, pr.y + ts)
    p4 = Vector2(pr.x, pr.y + ts)

    pygame.draw.polygon(screen, color, [p1, p2, p3, p4])
    pygame.draw.lines(screen, trim, True, [p1, p2, p3, p4], width=w)


def draw_fov_line(screen: Surface, tx: int, ty: int, settings: Settings):
    """Draws a 2D FOV line from (0,0) to tile at mouse cursor (tx, ty)."""
    tiles = bresenham_full(0, 0, tx, ty)

    ts = settings.tile_size
    color = Color(settings.fov_line_color)
    trim = Color(settings.fov_line_trim_color)
    for fx, fy in tiles:
        draw_fov_tile(screen, Vector2(fx * ts, fy * ts), ts, color, trim)


def draw_fov_tile(screen: Surface, pr: Vector2, ts: int, color: Color, trim: Color):
    """Draws an FOV tile with reference point `pr` and tile size `ts`."""

    p1 = Vector2(pr.x, pr.y)
    p2 = Vector2(pr.x + ts, pr.y)
    p3 = Vector2(pr.x + ts, pr.y + ts)
    p4 = Vector2(pr.x, pr.y + ts)

    pygame.draw.polygon(screen, color, [p1, p2, p3, p4])
    pygame.draw.lines(screen, trim, True, [p1, p2, p3, p4])


def draw_floor(
    screen: Surface, pr: Vector2, ts: int, width: int, color: Color, trim: Color
):
    """Draws a floor tile with reference point `pr` and tile size `ts`."""
    p1 = Vector2(pr.x, pr.y)
    p2 = Vector2(pr.x + ts, pr.y)
    p3 = Vector2(pr.x + ts, pr.y + ts)
    p4 = Vector2(pr.x, pr.y + ts)

    pygame.draw.lines(screen, color, True, [p1, p2, p3, p4], width=2)


def draw_north_wall(
    screen: Surface,
    pr: Vector2,
    ts: int,
    sts: int,
    width: int,
    color: Color,
    trim: Color,
):
    """Draws a north wall w/reference `pr`, tile size `ts`, and subtile size `sts`."""
    p1 = Vector2(pr.x, pr.y)
    p2 = Vector2(pr.x + ts, pr.y)
    p3 = Vector2(pr.x + ts, pr.y + sts)
    p4 = Vector2(pr.x, pr.y + sts)

    pygame.draw.polygon(screen, color, [p1, p2, p3, p4])
    pygame.draw.lines(screen, trim, True, [p1, p2, p3, p4], width=width)


def draw_west_wall(
    screen: Surface,
    pr: Vector2,
    ts: int,
    sts: int,
    width: int,
    color: Color,
    trim: Color,
):
    """Draws a north wall w/reference `pr`, tile size `ts`, and subtile size `sts`."""
    p1 = Vector2(pr.x, pr.y)
    p2 = Vector2(pr.x + sts, pr.y)
    p3 = Vector2(pr.x + sts, pr.y + ts)
    p4 = Vector2(pr.x, pr.y + ts)

    pygame.draw.polygon(screen, color, [p1, p2, p3, p4])
    pygame.draw.lines(screen, trim, True, [p1, p2, p3, p4], width=width)


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


def draw_subgrid(screen: Surface, settings: Settings):
    """Draws subtiles on base of tilemap according to dimensions."""
    color = settings.floor_trim_color
    ts = settings.tile_size
    sts = settings.tile_size / settings.subtiles_xy
    xdims, ydims = settings.xdims, settings.ydims

    for dx in range(1, xdims * settings.subtiles_xy):
        x1 = dx * sts
        y1 = 0
        x2 = dx * sts
        y2 = ydims * ts
        pygame.draw.line(screen, color, (x1, y1), (x2, y2))

    for dy in range(1, ydims * settings.subtiles_xy):
        x1 = 0
        y1 = dy * sts
        x2 = xdims * ts
        y2 = dy * sts
        pygame.draw.line(screen, color, (x1, y1), (x2, y2))


def draw_map(
    screen: Surface,
    tilemap: TileMap,
    visible_tiles: Dict[Tuple[int, int], VisibleTile],
    settings: Settings,
):
    """Renders the Tilemap, accounting for FOV."""
    # Row is y; col is x
    for ty, row_data in enumerate(tilemap.tiles):
        for tx, tile in enumerate(row_data):
            visible_tile = visible_tiles.get((tx, ty))
            if visible_tile:
                draw_tile(screen, tile, visible_tile, settings)


def draw_line_to_cursor(
    screen: Surface, px: int, py: int, mx: int, my: int, settings: Settings
):
    """Draws a line from player to mouse cursor.

    `px, py`: int
        player tile position.
    `mx, my`: int
        mouse cursor position.
    """
    ts = settings.tile_size
    mid = settings.tile_size * 0.5
    line_width = settings.line_width

    pygame.draw.line(
        screen,
        Color("red"),
        (px * ts + mid, py * ts + mid),
        (mx, my),
        line_width,
    )


def draw_tile_at_cursor(
    screen: Surface, tx: int, ty: int, settings: Settings, line=True
):
    """Draws border around Tile at cursor.  Also draws line if `line=True`."""
    ts = settings.tile_size
    tile_mid = ts * 0.5
    w = settings.line_width
    rx, ry = tx * ts, ty * ts

    if line:
        pygame.draw.line(
            screen,
            Color("red"),
            (tile_mid, tile_mid),
            (rx + tile_mid, ry + tile_mid),
            w,
        )

    pygame.draw.lines(
        screen,
        Color("yellow"),
        True,
        [(rx, ry), (rx + ts, ry), (rx + ts, ry + ts), (rx, ry + ts)],
    )


def draw_player(screen: Surface, player_img: Surface, px: int, py: int, tile_size: int):
    """Renders the player (always visible) on the Tilemap."""
    screen.blit(player_img, (px * tile_size, py * tile_size))


#   ########    ####    ##    ##
#   ##        ##    ##  ##    ##
#   ######    ##    ##  ##    ##
#   ##        ##    ##   ##  ##
#   ##         ######      ##


def fov_calc(
    ox: int, oy: int, tilemap: TileMap, fov_map: FovMap, radius: int
) -> Dict[Tuple[int, int], VisibleTile]:
    """Returns visible tiles (and substructures) from given origin (ox, oy).

    #### Parameters

     `ox`, `oy`: int
         Origin coordinates of the current Unit.
     `radius`: int
         Current unit's FOV radius.
    """
    tm = tilemap
    origin = tm.tile_at(ox, oy)
    xdims, ydims = tm.xdims, tm.ydims
    _wall_n = origin.wall_n > 0
    _wall_w = origin.wall_w > 0
    _structure = origin.structure > 0
    visible_tiles = {(ox, oy): VisibleTile(True, _structure, _wall_n, _wall_w)}

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

    vis5 = get_visible_tiles_56(ox, oy, origin, max_x, max_y, tm, fov_map.octant_5)
    update_visible_tiles(visible_tiles, vis5)

    vis6 = get_visible_tiles_56(ox, oy, origin, max_y, max_x, tm, fov_map.octant_6)
    update_visible_tiles(visible_tiles, vis6)

    # --- Octants 7-8 --- #
    max_x, max_y = boundary_radii(ox, oy, xdims, ydims, Octant.O8, radius)

    vis7 = get_visible_tiles_7(ox, oy, origin, max_y, max_x, tm, fov_map.octant_7)
    update_visible_tiles(visible_tiles, vis7)

    vis8 = get_visible_tiles_8(ox, oy, origin, max_x, max_y, tm, fov_map.octant_8)
    update_visible_tiles(visible_tiles, vis8)

    return visible_tiles


def get_visible_tiles_1(
    ox: int,
    oy: int,
    max_pri: int,
    max_sec: int,
    tilemap: TileMap,
    fov_octant: FovOctant,
) -> List[Tuple[int, int, VisibleTile]]:
    """Returns list of visible tiles and substructures in Octant 1."""
    fov_tiles = fov_octant.tiles
    pri_ix = fov_octant.max_fov_ix[max_pri + 1]
    sec_ix = max_sec
    visible_tiles = []
    blocked_bits: int = 0

    # Primary index and visibility of previous tile
    prev_pri: int = 0
    prev_vis: bool = False

    for fov_tile in fov_tiles[1:pri_ix]:
        dpri = fov_tile.dpri
        dsec = fov_tile.dsec
        visible_bits = fov_tile.visible_bits

        if dsec > sec_ix:
            continue

        if is_visible(visible_bits, blocked_bits):
            # For Octants 1 and 2, a tile may be blocked by its own N/W walls
            tx, ty = ox + fov_tile.rx, oy + fov_tile.ry
            tile = tilemap.tile_at(tx, ty)
            wall_n_bits = fov_tile.wall_n_bits
            wall_w_bits = fov_tile.wall_w_bits
            structure_bits = fov_tile.structure_bits

            _tile = False
            _structure = False
            _wall_w = False
            _wall_n = False
            _wall_w_vis = False
            _wall_n_vis = False

            # Check West wall before North; both walls before tile
            if tile.wall_w:
                _wall_w = True

                if is_visible(wall_w_bits, blocked_bits):
                    blocked_bits |= wall_w_bits
                    _wall_w_vis = True

            if tile.wall_n:
                _wall_n = True

                if (prev_vis and prev_pri == dpri) or is_visible(
                    wall_n_bits, blocked_bits
                ):
                    blocked_bits |= wall_n_bits
                    _wall_n_vis = True

            # 2nd tile visibility check after adding own walls
            if is_visible(visible_bits, blocked_bits):
                prev_vis = True
                _tile = True

                if tile.structure:
                    blocked_bits |= structure_bits
                    _structure = True
            else:
                prev_vis = False
                _wall_n = _wall_n_vis
                _wall_w = _wall_w_vis

            prev_pri = dpri
            vis_tile = VisibleTile(_tile, _structure, _wall_n, _wall_w)
            visible_tiles.append((tx, ty, vis_tile))

        else:
            if prev_vis and dpri == prev_pri:
                tx, ty = ox + fov_tile.rx, oy + fov_tile.ry
                tile = tilemap.tile_at(tx, ty)

                if tile.wall_n:
                    vis_tile = VisibleTile(False, False, True, False)
                    visible_tiles.append((tx, ty, vis_tile))

            prev_vis = False
            prev_pri = dpri

    return visible_tiles


def get_visible_tiles_2(
    ox: int,
    oy: int,
    max_pri: int,
    max_sec: int,
    tilemap: TileMap,
    fov_octant: FovOctant,
) -> List[Tuple[int, int, VisibleTile]]:
    """Returns list of visible tiles and substructures in Octant 2."""
    fov_tiles = fov_octant.tiles
    pri_ix = fov_octant.max_fov_ix[max_pri + 1]
    sec_ix = max_sec
    visible_tiles = []
    blocked_bits: int = 0

    # Primary index and visibility of previous tile
    prev_pri: int = 0
    prev_vis: bool = False

    for fov_tile in fov_tiles[1:pri_ix]:
        dpri = fov_tile.dpri
        dsec = fov_tile.dsec
        visible_bits = fov_tile.visible_bits

        if dsec > sec_ix:
            continue

        if is_visible(visible_bits, blocked_bits):
            # For Octants 1 and 2, a tile may be blocked by its own N/W walls
            tx, ty = ox + fov_tile.rx, oy + fov_tile.ry
            tile = tilemap.tile_at(tx, ty)
            wall_n_bits = fov_tile.wall_n_bits
            wall_w_bits = fov_tile.wall_w_bits
            structure_bits = fov_tile.structure_bits

            _tile = False
            _structure = False
            _wall_w = False
            _wall_n = False
            _wall_w_vis = False
            _wall_n_vis = False

            # Check North wall before West; both walls before tile
            if tile.wall_n:
                _wall_n = True

                if is_visible(wall_n_bits, blocked_bits):
                    blocked_bits |= wall_n_bits
                    _wall_n_vis = True

            if tile.wall_w:
                _wall_w = True

                if (prev_vis and prev_pri == dpri) or is_visible(
                    wall_w_bits, blocked_bits
                ):
                    blocked_bits |= wall_w_bits
                    _wall_w_vis = True

            # 2nd tile visibility check after adding own walls
            if is_visible(visible_bits, blocked_bits):
                prev_vis = True
                _tile = True

                if tile.structure:
                    blocked_bits |= structure_bits
                    _structure = True
            else:
                prev_vis = False
                _wall_n = _wall_n_vis
                _wall_w = _wall_w_vis

            prev_pri = dpri
            vis_tile = VisibleTile(_tile, _structure, _wall_n, _wall_w)
            visible_tiles.append((tx, ty, vis_tile))

        else:
            if prev_vis and dpri == prev_pri:
                tx, ty = ox + fov_tile.rx, oy + fov_tile.ry
                tile = tilemap.tile_at(tx, ty)

                if tile.wall_w:
                    vis_tile = VisibleTile(False, False, False, True)
                    visible_tiles.append((tx, ty, vis_tile))

            prev_vis = False
            prev_pri = dpri

    return visible_tiles


def get_visible_tiles_3(
    ox: int,
    oy: int,
    origin: Tile,
    max_pri: int,
    max_sec: int,
    tilemap: TileMap,
    fov_octant: FovOctant,
) -> List[Tuple[int, int, VisibleTile]]:
    """Returns list of visible tiles and substructures in Octant 3."""
    fov_tiles = fov_octant.tiles
    pri_ix = fov_octant.max_fov_ix[max_pri + 1]
    sec_ix = max_sec + 1
    visible_tiles = []
    blocked_bits: int = 0

    # Add West wall blocking bits for origin tile
    if origin.wall_w:
        blocked_bits |= fov_tiles[0].wall_w_bits

    for fov_tile in fov_tiles[1:pri_ix]:
        dsec = fov_tile.dsec
        visible_bits = fov_tile.visible_bits

        if dsec < sec_ix and is_visible(visible_bits, blocked_bits):
            # For Octants 3 and 4, a tile may be blocked by its own N wall
            tx, ty = ox + fov_tile.rx, oy + fov_tile.ry
            tile = tilemap.tile_at(tx, ty)
            wall_n_bits = fov_tile.wall_n_bits
            wall_w_bits = fov_tile.wall_w_bits
            structure_bits = fov_tile.structure_bits

            _tile = False
            _structure = False
            _wall_w = False
            _wall_n = False
            _wall_n_vis = False

            # Check North wall before tile
            if tile.wall_n:
                _wall_n = True

                if is_visible(wall_n_bits, blocked_bits):
                    blocked_bits |= wall_n_bits
                    _wall_n_vis = True

            # NOTE: 2nd visibility check after adding own walls
            if is_visible(visible_bits, blocked_bits):
                _tile = True

                if tile.wall_w:
                    blocked_bits |= wall_w_bits
                    _wall_w = True
                if tile.structure:
                    blocked_bits |= structure_bits
                    _structure = True
            else:
                _wall_n = _wall_n_vis

            vis_tile = VisibleTile(_tile, _structure, _wall_n, _wall_w)
            visible_tiles.append((tx, ty, vis_tile))

    return visible_tiles


def get_visible_tiles_4(
    ox: int,
    oy: int,
    origin: Tile,
    max_pri: int,
    max_sec: int,
    tilemap: TileMap,
    fov_octant: FovOctant,
) -> List[Tuple[int, int, VisibleTile]]:
    """Returns list of visible tiles and substructures in Octant 4."""
    fov_tiles = fov_octant.tiles
    pri_ix = fov_octant.max_fov_ix[max_pri + 1]
    sec_ix = max_sec
    visible_tiles = []
    blocked_bits: int = 0

    # Add West wall blocking bits for origin tile
    if origin.wall_w:
        blocked_bits |= fov_tiles[0].wall_w_bits

    # Primary index and visibility of previous tile
    prev_pri: int = 0
    prev_vis: bool = False

    for fov_tile in fov_tiles[1:pri_ix]:
        dpri = fov_tile.dpri
        dsec = fov_tile.dsec
        visible_bits = fov_tile.visible_bits

        if dsec > sec_ix:
            continue

        if is_visible(visible_bits, blocked_bits):
            # For Octants 3 and 4, a tile may be blocked by its own N wall
            tx, ty = ox + fov_tile.rx, oy + fov_tile.ry
            tile = tilemap.tile_at(tx, ty)
            wall_n_bits = fov_tile.wall_n_bits
            wall_w_bits = fov_tile.wall_w_bits
            structure_bits = fov_tile.structure_bits

            _tile = False
            _structure = False
            _wall_w = False
            _wall_n = False
            _wall_n_vis = False

            if tile.wall_n:
                _wall_n = True
                if (prev_vis and prev_pri == dpri) or is_visible(
                    wall_n_bits, blocked_bits
                ):
                    blocked_bits |= wall_n_bits
                    _wall_n_vis = True

            # NOTE: 2nd visibility check after adding own walls
            if is_visible(visible_bits, blocked_bits):
                prev_vis = True
                _tile = True

                if tile.wall_w:
                    blocked_bits |= wall_w_bits
                    _wall_w = True
                if tile.structure:
                    blocked_bits |= structure_bits
                    _structure = True
            else:
                prev_vis = False
                _wall_n = _wall_n_vis

            prev_pri = dpri
            vis_tile = VisibleTile(_tile, _structure, _wall_n, _wall_w)
            visible_tiles.append((tx, ty, vis_tile))

        else:
            if prev_vis and dpri == prev_pri:
                tx, ty = ox + fov_tile.rx, oy + fov_tile.ry
                tile = tilemap.tile_at(tx, ty)

                if tile.wall_n:
                    vis_tile = VisibleTile(False, False, True, False)
                    visible_tiles.append((tx, ty, vis_tile))

            prev_vis = False
            prev_pri = dpri

    return visible_tiles


def get_visible_tiles_56(
    ox: int,
    oy: int,
    origin: Tile,
    max_pri: int,
    max_sec: int,
    tilemap: TileMap,
    fov_octant: FovOctant,
) -> List[Tuple[int, int, VisibleTile]]:
    """Returns list of visible tiles and substructures in Octants 5 and 6."""
    fov_tiles = fov_octant.tiles
    pri_ix = fov_octant.max_fov_ix[max_pri + 1]
    sec_ix = max_sec + 1
    visible_tiles = []
    blocked_bits: int = 0

    # Add North and West wall blocking bits for origin tile
    if origin.wall_n:
        blocked_bits |= fov_tiles[0].wall_n_bits
    if origin.wall_w:
        blocked_bits |= fov_tiles[0].wall_w_bits

    for fov_tile in fov_tiles[1:pri_ix]:
        dsec = fov_tile.dsec
        visible_bits = fov_tile.visible_bits

        if dsec < sec_ix and is_visible(visible_bits, blocked_bits):
            # For Octants 5 and 6, tiles are not blocked by their own N/W walls
            tx, ty = ox + fov_tile.rx, oy + fov_tile.ry
            tile = tilemap.tile_at(tx, ty)
            wall_n_bits = fov_tile.wall_n_bits
            wall_w_bits = fov_tile.wall_w_bits
            structure_bits = fov_tile.structure_bits

            _tile = True
            _structure = False
            _wall_w = False
            _wall_n = False

            if tile.structure:
                blocked_bits |= structure_bits
                _structure = True
            if tile.wall_n:
                blocked_bits |= wall_n_bits
                _wall_n = True
            if tile.wall_w:
                blocked_bits |= wall_w_bits
                _wall_w = True

            vis_tile = VisibleTile(_tile, _structure, _wall_n, _wall_w)
            visible_tiles.append((tx, ty, vis_tile))

    return visible_tiles


def get_visible_tiles_7(
    ox: int,
    oy: int,
    origin: Tile,
    max_pri: int,
    max_sec: int,
    tilemap: TileMap,
    fov_octant: FovOctant,
) -> List[Tuple[int, int, VisibleTile]]:
    """Returns list of visible tiles and substructures in Octant 7."""
    fov_tiles = fov_octant.tiles
    pri_ix = fov_octant.max_fov_ix[max_pri + 1]
    sec_ix = max_sec
    visible_tiles = []
    blocked_bits: int = 0

    # Add North wall blocking bits for origin tile
    if origin.wall_n:
        blocked_bits |= fov_tiles[0].wall_n_bits

    # Primary index and visibility of previous tile
    prev_pri: int = 0
    prev_vis: bool = False

    for fov_tile in fov_tiles[1:pri_ix]:
        dpri = fov_tile.dpri
        dsec = fov_tile.dsec
        visible_bits = fov_tile.visible_bits

        if dsec > sec_ix:
            continue

        if is_visible(visible_bits, blocked_bits):
            # For Octants 7 and 8, a tile may be blocked by its own W wall
            tx, ty = ox + fov_tile.rx, oy + fov_tile.ry
            tile = tilemap.tile_at(tx, ty)
            wall_n_bits = fov_tile.wall_n_bits
            wall_w_bits = fov_tile.wall_w_bits
            structure_bits = fov_tile.structure_bits

            _tile = False
            _structure = False
            _wall_w_vis = False
            _wall_w = False
            _wall_n = False

            # Check West wall before North wall and tiles
            if tile.wall_w:
                _wall_w = True

                if (prev_vis and prev_pri == dpri) or is_visible(
                    wall_w_bits, blocked_bits
                ):
                    blocked_bits |= wall_w_bits
                    _wall_w_vis = True

            # NOTE: 2nd visibility check after adding own walls
            if is_visible(visible_bits, blocked_bits):
                prev_vis = True
                _tile = True

                if tile.wall_n:
                    blocked_bits |= wall_n_bits
                    _wall_n = True
                if tile.structure:
                    blocked_bits |= structure_bits
                    _structure = True
            else:
                _wall_w = _wall_w_vis
                prev_vis = False

            prev_pri = dpri
            vis_tile = VisibleTile(_tile, _structure, _wall_n, _wall_w)
            visible_tiles.append((tx, ty, vis_tile))

        else:
            if prev_vis and dpri == prev_pri:
                tx, ty = ox + fov_tile.rx, oy + fov_tile.ry
                tile = tilemap.tile_at(tx, ty)

                if tile.wall_w:
                    vis_tile = VisibleTile(False, False, False, True)
                    visible_tiles.append((tx, ty, vis_tile))

            prev_vis = False
            prev_pri = dpri

    return visible_tiles


def get_visible_tiles_8(
    ox: int,
    oy: int,
    origin: Tile,
    max_pri: int,
    max_sec: int,
    tilemap: TileMap,
    fov_octant: FovOctant,
) -> List[Tuple[int, int, VisibleTile]]:
    """Returns list of visible tiles and substructures in Octant 8."""
    fov_tiles = fov_octant.tiles
    pri_ix = fov_octant.max_fov_ix[max_pri + 1]
    sec_ix = max_sec + 1
    visible_tiles = []
    blocked_bits: int = 0

    # Add North wall blocking bits for origin tile
    if origin.wall_n:
        blocked_bits |= fov_tiles[0].wall_n_bits

    for fov_tile in fov_tiles[1:pri_ix]:
        dsec = fov_tile.dsec
        visible_bits = fov_tile.visible_bits

        if dsec < sec_ix and is_visible(visible_bits, blocked_bits):
            # For Octants 7 and 8, a tile may be blocked by its own W wall
            tx, ty = ox + fov_tile.rx, oy + fov_tile.ry
            tile = tilemap.tile_at(tx, ty)
            wall_n_bits = fov_tile.wall_n_bits
            wall_w_bits = fov_tile.wall_w_bits
            structure_bits = fov_tile.structure_bits

            _tile = False
            _structure = False
            _wall_w_vis = False
            _wall_w = False
            _wall_n = False

            # Check West wall before checking tiles
            if tile.wall_w:
                _wall_w = True

                if is_visible(wall_w_bits, blocked_bits):
                    blocked_bits |= wall_w_bits
                    _wall_w_vis = True

            # NOTE: 2nd visibility check after adding own walls
            if is_visible(visible_bits, blocked_bits):
                _tile = True

                if tile.wall_n:
                    blocked_bits |= wall_n_bits
                    _wall_n = True
                if tile.structure:
                    blocked_bits |= structure_bits
                    _structure = True
            else:
                _wall_w = _wall_w_vis

            vis_tile = VisibleTile(_tile, _structure, _wall_n, _wall_w)
            visible_tiles.append((tx, ty, vis_tile))

    return visible_tiles


def is_visible(visible_bits: int, blocked_bits: int) -> bool:
    """Returns `True` if the tile has at least one visible bit not in FOV's blocked bits."""
    return visible_bits - (visible_bits & blocked_bits) > 0


def update_visible_tiles(
    to_dict: Dict[Tuple[int, int], VisibleTile],
    from_list: List[Tuple[int, int, VisibleTile]],
):
    """ "Updates full dictionary of visible tiles from per-octant list.

    Incoming list of tuples is in form (x, y, visible_tile).
    """
    for x, y, visible_tile in from_list:
        current = to_dict.get((x, y), VisibleTile(False, False, False, False))
        current.update(visible_tile)
        to_dict[(x, y)] = current


#    ######      ##     ##    ##  ########
#   ##         ##  ##   ###  ###  ##
#   ##   ###  ##    ##  ## ## ##  ######
#   ##    ##  ########  ##    ##  ##
#    ######   ##    ##  ##    ##  ########


def run_game(tilemap: TileMap, settings: Settings):
    """Renders the FOV display using Pygame."""
    # --- Pygame setup --- #
    pygame.init()
    pygame.display.set_caption("2D Advanced FOV")
    screen = pygame.display.set_mode((1280, 720))
    pygame.key.set_repeat(0)
    clock = pygame.time.Clock()
    running = True

    # --- Player Setup --- #
    px, py = 0, 0
    player_img = pygame.image.load("assets/paperdoll_1.png").convert_alpha()

    # --- Map Setup --- #
    radius = settings.fov_radius
    tile_size = settings.tile_size
    fov_map = FovMap(settings.qbits)
    visible_tiles = fov_calc(0, 0, tilemap, fov_map, radius)

    # --- HUD Setup --- #
    show_player_line = False
    show_fov_line = False
    show_cursor = True

    # --- Initial Draw --- #
    draw_map(screen, tilemap, visible_tiles, settings)
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
                if event.dict["key"] == pygame.K_c:
                    show_cursor = not show_cursor
                    redraw = True
                if event.dict["key"] == pygame.K_f:
                    show_fov_line = not show_fov_line
                    redraw = True
                if event.dict["key"] == pygame.K_r:
                    show_player_line = not show_player_line
                    redraw = True

        # Check for mouse movement
        mdx, mdy = pygame.mouse.get_rel()
        if mdx != 0 or mdy != 0:
            redraw = True

        # --- Rendering --- #
        if redraw:
            # fill the screen with a color to wipe away anything from last frame
            screen.fill("black")
            mx, my = pygame.mouse.get_pos()
            visible_tiles = fov_calc(px, py, tilemap, fov_map, radius)
            draw_map(screen, tilemap, visible_tiles, settings)
            draw_player(screen, player_img, px, py, tile_size)

            tx, ty = get_tile_at_cursor(mx, my, tile_size)

            if show_fov_line:
                draw_fov_line(screen, tx, ty, settings)
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
    print("\n=====  2D Advanced FOV Testing  =====\n")
    pygame.freetype.init()
    # FOV Blockers: (structure: int, north_wall: int, west_wall: int)
    blocked: Dict[Tuple[int, int], Blockers] = {
        (4, 4): Blockers(wall_n=2),
        (5, 4): Blockers(wall_w=2),
        (8, 4): Blockers(wall_n=2, wall_w=2),
        (10, 4): Blockers(wall_n=2),
        (13, 7): Blockers(structure=True),
        (14, 6): Blockers(structure=True),
        (15, 0): Blockers(wall_w=2),
        (15, 1): Blockers(wall_n=2),
    }
    settings = Settings(
        1280,
        720,
        Coords(16, 9),
        64,
        1,
        8,
        QBits.Q64,
        Font(None, size=16),
        Color("snow"),
    )
    tilemap = TileMap(blocked, settings)
    run_game(tilemap, settings)
